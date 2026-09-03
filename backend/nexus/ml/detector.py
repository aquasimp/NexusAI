"""Multi-signal anomaly detection.

Per (service, metric):
  1. Harmonic (Fourier) ridge regression on time-of-day  -> seasonal mean
  2. AR(1) whitening of residuals                        -> i.i.d.-ish innovations
  3. Robust scaling by MAD                               -> z-scores

Per service (multivariate over the 6 whitened z's):
  4. Mahalanobis distance with Ledoit-Wolf shrinkage covariance
  5. IsolationForest on the same vectors
  6. Both mapped to empirical percentiles of the TRAINING score distribution
     and fused; threshold = `detect_quantile` of training percentiles, gated by
     k-of-n persistence + hysteresis to suppress single-tick flapping.

Everything is fitted on clean warm-up history and evaluated on unseen ticks.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import IsolationForest

from ..sim.topology import METRICS, SERVICES

DAY = 86400.0
LOG_METRICS = {"latency_p50", "latency_p95", "rps"}


def _design(times: np.ndarray, harmonics: int) -> np.ndarray:
    tod = (times % DAY) / DAY
    cols = [np.ones_like(tod)]
    for k in range(1, harmonics + 1):
        cols += [np.sin(2 * np.pi * k * tod), np.cos(2 * np.pi * k * tod)]
    return np.column_stack(cols)


def _transform(metric: str, x: np.ndarray) -> np.ndarray:
    if metric in LOG_METRICS:
        return np.log1p(np.maximum(x, 0.0))
    if metric == "error_rate":
        return np.sqrt(np.maximum(x, 0.0))          # variance stabilising
    return x


@dataclass
class MetricModel:
    coef: np.ndarray
    scale: float
    rho: float
    mean_resid: float


@dataclass
class ServiceModel:
    metrics: dict[str, MetricModel]
    precision: np.ndarray
    maha_train: np.ndarray            # sorted training Mahalanobis scores
    iforest: IsolationForest
    if_train: np.ndarray              # sorted training -score_samples
    fused_train: np.ndarray           # sorted training fused percentiles


@dataclass
class DetectorState:
    """Streaming state — separable from fitted params so the benchmark can run
    many independent episodes against one fitted model."""
    last_resid: dict[tuple[str, str], float] = field(default_factory=dict)
    recent: dict[str, deque] = field(default_factory=dict)
    firing: dict[str, bool] = field(default_factory=dict)


class Detector:
    def __init__(self, harmonics: int = 3, quantile: float = 0.995,
                 persist_k: int = 3, persist_n: int = 5, seed: int = 11):
        self.h = harmonics
        self.q = quantile
        self.k = persist_k
        self.n = persist_n
        self.seed = seed
        self.models: dict[str, ServiceModel] = {}
        self.threshold: float = 0.0
        self.fitted = False

    # -------------------------------------------------------------- fitting
    def fit(self, times: np.ndarray, history: dict[str, dict[str, np.ndarray]]) -> "Detector":
        X = _design(times, self.h)
        XtX = X.T @ X + 1e-6 * np.eye(X.shape[1])
        all_fused = []

        for sid, series in history.items():
            mmodels, Z = {}, []
            for m in METRICS:
                if SERVICES[sid].kind == "external" and m in ("cpu", "mem"):
                    mmodels[m] = MetricModel(np.zeros(X.shape[1]), 1.0, 0.0, 0.0)
                    Z.append(np.zeros(len(times)))
                    continue
                y = _transform(m, np.asarray(series[m], dtype=float))
                coef = np.linalg.solve(XtX, X.T @ y)
                resid = y - X @ coef
                rho = float(np.clip(
                    np.corrcoef(resid[:-1], resid[1:])[0, 1] if len(resid) > 3 else 0.0,
                    -0.95, 0.95))
                if not np.isfinite(rho):
                    rho = 0.0
                innov = resid[1:] - rho * resid[:-1]
                med = float(np.median(innov))
                mad = float(np.median(np.abs(innov - med)))
                scale = max(1.4826 * mad, 1e-4)
                mmodels[m] = MetricModel(coef, scale, rho, med)
                z = np.concatenate([[0.0], (innov - med) / scale])
                Z.append(np.clip(z, -40, 40))

            Zm = np.column_stack(Z)
            lw = LedoitWolf().fit(Zm)
            prec = np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(Zm.shape[1]))
            maha = np.einsum("ij,jk,ik->i", Zm, prec, Zm)

            iso = IsolationForest(n_estimators=160, max_samples=min(1024, len(Zm)),
                                  contamination=0.01, random_state=self.seed).fit(Zm)
            ifs = -iso.score_samples(Zm)

            maha_s, if_s = np.sort(maha), np.sort(ifs)
            p1 = np.searchsorted(maha_s, maha, "right") / len(maha_s)
            p2 = np.searchsorted(if_s, ifs, "right") / len(if_s)
            fused = 0.65 * p1 + 0.35 * p2

            self.models[sid] = ServiceModel(mmodels, prec, maha_s, iso, if_s, np.sort(fused))
            all_fused.append(fused)

        self.threshold = float(np.quantile(np.max(np.column_stack(all_fused), axis=1), self.q))
        self.fitted = True
        return self

    # ------------------------------------------------------------- scoring
    def new_state(self) -> DetectorState:
        return DetectorState(
            last_resid={(s, m): 0.0 for s in self.models for m in METRICS},
            recent={s: deque(maxlen=self.n) for s in self.models},
            firing={s: False for s in self.models},
        )

    def score_frame(self, state: DetectorState, sim_ts: float,
                    frame: dict[str, dict[str, float]]) -> dict:
        x = _design(np.array([sim_ts]), self.h)[0]
        per_service = {}
        for sid, sm in self.models.items():
            zs, resids = {}, {}
            for m in METRICS:
                mm = sm.metrics[m]
                y = _transform(m, np.array([frame[sid].get(m, 0.0)]))[0]
                r = y - float(x @ mm.coef)
                innov = r - mm.rho * state.last_resid[(sid, m)]
                state.last_resid[(sid, m)] = r
                z = float(np.clip((innov - mm.mean_resid) / mm.scale, -40, 40))
                zs[m], resids[m] = z, r

            v = np.array([zs[m] for m in METRICS])
            maha = float(v @ sm.precision @ v)
            ifs = float(-sm.iforest.score_samples(v.reshape(1, -1))[0])
            p = (0.65 * np.searchsorted(sm.maha_train, maha, "right") / len(sm.maha_train)
                 + 0.35 * np.searchsorted(sm.if_train, ifs, "right") / len(sm.if_train))

            state.recent[sid].append(p)
            above = sum(1 for q in state.recent[sid] if q >= self.threshold)
            if state.firing[sid]:
                state.firing[sid] = above >= 1                     # hysteresis
            else:
                state.firing[sid] = above >= self.k
            contrib = sorted(((m, abs(zs[m])) for m in METRICS), key=lambda t: -t[1])

            per_service[sid] = {
                "score": round(p, 5), "mahalanobis": round(maha, 3),
                "iforest": round(ifs, 4), "z": {m: round(zs[m], 3) for m in METRICS},
                "firing": bool(state.firing[sid]),
                "top_metrics": [{"metric": m, "abs_z": round(z, 2)} for m, z in contrib[:3]],
            }

        firing = [s for s, r in per_service.items() if r["firing"]]
        return {
            "threshold": round(self.threshold, 5),
            "system_score": round(max(r["score"] for r in per_service.values()), 5),
            "services": per_service,
            "firing": firing,
            "anomalous_fraction": round(len(firing) / len(per_service), 3),
        }
