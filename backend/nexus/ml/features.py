"""Incident-level feature extraction for root-cause classification.

Deliberately class-agnostic: no feature encodes "which scenario is armed", and
service identity is generalised to `kind` so the model cannot memorise
service->label. 35 features, fixed order.
"""
from __future__ import annotations

import numpy as np

from ..sim.topology import METRICS, SERVICES
from .changepoint import mann_kendall_tau, trend_slope

KINDS = ("edge", "app", "datastore", "cache", "external")
LOG_PATTERNS = ("timeout", "lock_wait", "oom", "schema_reject",
                "pool_exhausted", "cache_miss", "circuit_open", "slow_query")

FEATURE_NAMES = (
    [f"leader_kind_{k}" for k in KINDS]
    + ["leader_z_rps", "leader_z_p50", "leader_z_p95", "leader_z_err",
       "leader_z_cpu", "leader_z_mem",
       "leader_mem_slope", "leader_mem_tau", "leader_err_slope", "leader_p95_slope",
       "entry_z_rps", "anomalous_fraction", "onset_spread_norm", "leader_lead_norm",
       "deploy_recent", "deploy_on_leader",
       "err_dominance", "lat_dominance", "sat_index",
       "external_err_share", "p95_slo_ratio", "err_slo_ratio"]
    + [f"log_{p}" for p in LOG_PATTERNS]
)
N_FEATURES = len(FEATURE_NAMES)
assert N_FEATURES == 35, N_FEATURES


def extract(window: dict, anomaly: dict, blame: dict, logs: list[dict],
            deploys: list[dict], tick_seconds: float) -> tuple[np.ndarray, dict]:
    leader = blame["leader"]
    zmat = window["z"]
    raw = window["raw"]                     # {sid: {metric: ndarray}}
    T = window["n"]
    idx = {m: i for i, m in enumerate(METRICS)}
    lz = zmat[leader]
    tail = slice(max(0, T - 40), T)

    f: list[float] = [1.0 if SERVICES[leader].kind == k else 0.0 for k in KINDS]

    peak = {m: float(np.max(np.abs(lz[tail, idx[m]]))) for m in METRICS}
    f += [peak["rps"], peak["latency_p50"], peak["latency_p95"],
          peak["error_rate"], peak["cpu"], peak["mem"]]

    mem = raw[leader]["mem"][tail]
    f += [trend_slope(mem), mann_kendall_tau(mem),
          trend_slope(raw[leader]["error_rate"][tail]),
          trend_slope(raw[leader]["latency_p95"][tail])]

    f.append(float(np.max(np.abs(zmat["api-gateway"][tail, idx["rps"]]))))
    f.append(anomaly["anomalous_fraction"])
    f.append(min(1.0, blame["onset_spread_s"] / (30 * tick_seconds)))
    row = next(r for r in blame["ranking"] if r["service"] == leader)
    f.append(min(1.0, row["onset_lead_s"] / (30 * tick_seconds)))

    recent = [d for d in deploys
              if 0 <= (window["t_start"] + T - 1 - d["tick"]) <= 60]
    f.append(1.0 if recent else 0.0)
    f.append(1.0 if any(d["service"] == leader for d in recent) else 0.0)

    e, l = peak["error_rate"], peak["latency_p95"]
    f += [e / (e + l + 1e-6), l / (e + l + 1e-6),
          float(np.tanh(peak["cpu"] * peak["rps"] / 40.0))]

    ext_err = sum(float(np.mean(raw[s]["error_rate"][tail]))
                  for s in SERVICES if SERVICES[s].kind == "external")
    tot_err = sum(float(np.mean(raw[s]["error_rate"][tail])) for s in SERVICES) + 1e-6
    f.append(ext_err / tot_err)
    f.append(min(12.0, float(np.mean(raw[leader]["latency_p95"][tail]))
                 / max(1e-6, SERVICES[leader].slo_p95_ms)))
    f.append(min(60.0, float(np.mean(raw[leader]["error_rate"][tail]))
                 / max(1e-6, SERVICES[leader].slo_error_pct)))

    recent_logs = [x for x in logs if x["tick"] >= window["t_start"] + T - 40]
    n = max(1, len(recent_logs))
    counts = {p: 0 for p in LOG_PATTERNS}
    for x in recent_logs:
        if x["pattern"] in counts:
            counts[x["pattern"]] += 1
    f += [counts[p] / n for p in LOG_PATTERNS]

    v = np.nan_to_num(np.array(f, dtype=float), nan=0.0, posinf=40.0, neginf=-40.0)
    return v, dict(zip(FEATURE_NAMES, v.round(4).tolist()))
