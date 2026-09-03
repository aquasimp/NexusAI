"""Root-cause classifier: multinomial logistic regression over incident
features, trained on seeded benchmark episodes with GroupKFold(seed) CV.

Two rankers are exposed and the UI always states which one produced the answer:
  * `learned`  — the trained LR (preferred; artifact at settings.model_path)
  * `rule`     — a transparent evidence scorer used as cold-start fallback
                 and as an independent cross-check in the UI
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..config import settings
from .features import FEATURE_NAMES

CLASSES = ("db_latency_saturation", "bad_deploy", "memory_leak", "traffic_surge",
           "dependency_outage", "api_error_explosion", "cascading_failure")


@dataclass
class RCAPrediction:
    ranker: str
    ranking: list[dict]          # [{class, probability, evidence:[...]}]
    top_class: str
    confidence: float
    margin: float


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(max_iter=4000, C=0.85, class_weight="balanced")),
    ])


def save(pipe: Pipeline, report: dict) -> None:
    joblib.dump({"pipeline": pipe, "features": list(FEATURE_NAMES),
                 "classes": list(pipe.classes_), "report": report},
                settings.model_path)


def load() -> dict | None:
    if not settings.model_path.exists():
        return None
    try:
        art = joblib.load(settings.model_path)
        if list(art.get("features", [])) != list(FEATURE_NAMES):
            return None                      # feature schema drift -> retrain
        return art
    except Exception:
        return None


# --------------------------------------------------------------- learned path
def predict_learned(art: dict, x: np.ndarray, fdict: dict) -> RCAPrediction:
    pipe: Pipeline = art["pipeline"]
    proba = pipe.predict_proba(x.reshape(1, -1))[0]
    lr: LogisticRegression = pipe.named_steps["lr"]
    xs = pipe.named_steps["scale"].transform(x.reshape(1, -1))[0]

    order = np.argsort(-proba)
    ranking = []
    for i in order:
        cls = pipe.classes_[i]
        contrib = lr.coef_[i] * xs
        top = np.argsort(-np.abs(contrib))[:5]
        ranking.append({
            "class": str(cls),
            "probability": round(float(proba[i]), 4),
            "evidence": [{
                "feature": FEATURE_NAMES[j],
                "value": round(float(x[j]), 4),
                "contribution": round(float(contrib[j]), 4),
                "direction": "supports" if contrib[j] > 0 else "contradicts",
            } for j in top],
        })
    p = float(proba[order[0]])
    m = p - float(proba[order[1]]) if len(order) > 1 else p
    return RCAPrediction("learned", ranking, str(pipe.classes_[order[0]]),
                         round(p, 4), round(m, 4))


# ------------------------------------------------------------- rule fallback
def _sig(x: float, c: float, k: float) -> float:
    return 1.0 / (1.0 + np.exp(-(x - c) / max(1e-6, k)))


RULES: dict[str, list[tuple[str, float, float, float]]] = {
    # class: [(feature, centre, width, weight)]
    "db_latency_saturation": [
        ("leader_kind_datastore", 0.5, 0.1, 2.6), ("leader_z_p95", 4.0, 2.0, 1.5),
        ("log_lock_wait", 0.02, 0.02, 1.5), ("log_slow_query", 0.01, 0.01, 0.9),
        ("deploy_on_leader", 0.5, 0.1, -1.6), ("leader_mem_tau", 0.6, 0.2, -1.0),
    ],
    "bad_deploy": [
        ("deploy_on_leader", 0.5, 0.1, 3.4), ("leader_z_err", 3.0, 2.0, 1.2),
        ("leader_z_p95", 3.0, 2.0, 1.0), ("lat_dominance", 0.35, 0.15, 0.7),
        ("leader_kind_app", 0.5, 0.1, 0.8), ("leader_mem_tau", 0.6, 0.2, -1.0),
    ],
    "memory_leak": [
        ("leader_mem_tau", 0.55, 0.2, 3.2), ("leader_z_mem", 3.5, 2.0, 2.0),
        ("log_oom", 0.01, 0.01, 1.8), ("deploy_on_leader", 0.5, 0.1, -1.2),
        ("leader_mem_slope", 0.05, 0.05, 1.0),
    ],
    "traffic_surge": [
        ("entry_z_rps", 3.5, 2.0, 3.0), ("sat_index", 0.6, 0.2, 1.6),
        ("leader_z_cpu", 3.0, 2.0, 1.2), ("deploy_recent", 0.5, 0.1, -1.4),
        ("err_dominance", 0.6, 0.2, -1.0),
    ],
    "dependency_outage": [
        ("leader_kind_external", 0.5, 0.1, 3.6), ("external_err_share", 0.25, 0.12, 2.2),
        ("log_timeout", 0.05, 0.04, 1.2), ("deploy_recent", 0.5, 0.1, -1.0),
    ],
    "api_error_explosion": [
        ("leader_kind_edge", 0.5, 0.1, 2.2), ("err_dominance", 0.6, 0.15, 2.6),
        ("log_schema_reject", 0.02, 0.02, 2.2), ("lat_dominance", 0.45, 0.15, -1.8),
        ("deploy_on_leader", 0.5, 0.1, 1.0),
    ],
    "cascading_failure": [
        ("anomalous_fraction", 0.55, 0.15, 2.8), ("onset_spread_norm", 0.35, 0.15, 1.8),
        ("leader_kind_cache", 0.5, 0.1, 2.2), ("log_timeout", 0.05, 0.04, 1.2),
        ("log_cache_miss", 0.01, 0.01, 1.4), ("deploy_recent", 0.5, 0.1, -1.0),
    ],
}


def predict_rule(x: np.ndarray, fdict: dict) -> RCAPrediction:
    scores, ev = {}, {}
    for cls, rules in RULES.items():
        s, items = 0.0, []
        for feat, c, k, w in rules:
            val = float(fdict.get(feat, 0.0))
            match = _sig(val, c, k)
            s += w * match
            items.append({"feature": feat, "value": round(val, 4),
                          "contribution": round(w * match, 4),
                          "direction": "supports" if w > 0 else "contradicts"})
        scores[cls] = s
        ev[cls] = sorted(items, key=lambda i: -abs(i["contribution"]))[:5]

    keys = list(scores)
    z = np.array([scores[k] for k in keys])
    p = np.exp(z - z.max()) / np.exp(z - z.max()).sum()
    order = np.argsort(-p)
    ranking = [{"class": keys[i], "probability": round(float(p[i]), 4),
                "evidence": ev[keys[i]]} for i in order]
    top = float(p[order[0]])
    return RCAPrediction("rule", ranking, keys[order[0]], round(top, 4),
                         round(top - float(p[order[1]]), 4))


class RCARanker:
    def __init__(self):
        self.art = load()

    def reload(self) -> None:
        self.art = load()

    @property
    def mode(self) -> str:
        return "learned" if self.art else "rule"

    def info(self) -> dict:
        if not self.art:
            return {"mode": "rule", "note": "No trained artifact found — "
                    "using transparent evidence scorer. Run `make train`.",
                    "classes": list(CLASSES)}
        return {"mode": "learned", "classes": self.art["classes"],
                "report": self.art["report"], "n_features": len(FEATURE_NAMES)}

    def predict(self, x: np.ndarray, fdict: dict) -> tuple[RCAPrediction, RCAPrediction]:
        rule = predict_rule(x, fdict)
        learned = predict_learned(self.art, x, fdict) if self.art else None
        return (learned or rule), rule
