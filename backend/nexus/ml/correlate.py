"""Dependency-aware fault localization ("blame ranking").

Blame(s) = 0.40·anomaly_magnitude
         + 0.24·onset_lead        (causes move first)
         + 0.24·upstreamness      (share of anomalous services that depend on s)
         + 0.12·deploy_proximity

Upstreamness is computed on the real dependency graph restricted to the
anomalous subgraph, which is what separates "the DB is slow" from
"five services are slow because the DB is slow".
"""
from __future__ import annotations

import numpy as np

from ..sim.topology import SERVICES, dependents_transitive
from .changepoint import onset_for_service


def localize(window: dict, anomaly: dict, deploys: list[dict],
             tick_seconds: float) -> dict:
    firing = anomaly["firing"] or [
        max(anomaly["services"], key=lambda s: anomaly["services"][s]["score"])]
    zmat = window["z"]                            # {sid: (T, n_metrics) ndarray}
    T = window["n"]

    onsets: dict[str, int] = {}
    for sid in firing:
        o = onset_for_service(zmat[sid])
        onsets[sid] = o if o is not None else T - 1
    earliest = min(onsets.values()) if onsets else 0
    latest = max(onsets.values()) if onsets else 0
    spread = max(1, latest - earliest)

    mags = {s: anomaly["services"][s]["score"] for s in firing}
    mmax = max(mags.values()) or 1.0
    firing_set = set(firing)

    rows = []
    for sid in firing:
        lead = 1.0 - (onsets[sid] - earliest) / spread
        deps_on_me = dependents_transitive(sid) & firing_set
        upstreamness = len(deps_on_me) / max(1, len(firing_set) - 1)
        dp = 0.0
        for d in deploys:
            if d["service"] == sid:
                age = (T - 1) - (d["tick"] - window["t_start"])
                dp = max(dp, float(np.exp(-max(0.0, age) / 40.0)))
        blame = (0.40 * mags[sid] / mmax + 0.24 * lead
                 + 0.24 * upstreamness + 0.12 * dp)
        rows.append({
            "service": sid, "kind": SERVICES[sid].kind, "blame": round(blame, 4),
            "anomaly_score": round(mags[sid], 4),
            "onset_tick": int(window["t_start"] + onsets[sid]),
            "onset_lead_s": round((latest - onsets[sid]) * tick_seconds, 1),
            "upstreamness": round(upstreamness, 3),
            "deploy_proximity": round(dp, 3),
            "top_metrics": anomaly["services"][sid]["top_metrics"],
        })
    rows.sort(key=lambda r: -r["blame"])
    return {
        "ranking": rows,
        "leader": rows[0]["service"],
        "affected": firing,
        "onset_tick": int(window["t_start"] + earliest),
        "onset_spread_s": round(spread * tick_seconds, 1),
        "propagation_path": _path(rows[0]["service"], firing_set),
    }


def _path(root: str, affected: set[str]) -> list[list[str]]:
    """BFS blast-radius edges from root outward through callers."""
    edges, seen, frontier = [], {root}, [root]
    while frontier:
        cur = frontier.pop(0)
        for s, spec in SERVICES.items():
            if cur in spec.deps and s in affected and s not in seen:
                edges.append([cur, s])
                seen.add(s)
                frontier.append(s)
    return edges
