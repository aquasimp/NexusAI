"""Impact model: SLO error-budget burn + revenue-at-risk + affected users.
All inputs are measured from the simulated telemetry; the monetary constants
are stated assumptions surfaced in the UI (never presented as measurements)."""
from __future__ import annotations

import numpy as np

from ..simulation.topology import REVENUE_PER_REQ, SERVICES, dependents_transitive

MONTHLY_BUDGET_MIN = 43200.0          # minutes in a 30-day month
ASSUMED_SESSION_REQS = 7.5            # requests per user session (assumption)


def estimate(window: dict, blame: dict, tick_seconds: float) -> dict:
    raw, T = window["raw"], window["n"]
    tail = slice(max(0, T - 40), T)
    dur_min = (T - (blame["onset_tick"] - window["t_start"])) * tick_seconds / 60.0
    dur_min = max(tick_seconds / 60.0, dur_min)

    rows, revenue, users = [], 0.0, 0.0
    for sid in SERVICES:
        spec = SERVICES[sid]
        err = float(np.mean(raw[sid]["error_rate"][tail]))
        p95 = float(np.mean(raw[sid]["latency_p95"][tail]))
        rps = float(np.mean(raw[sid]["rps"][tail]))
        base_err = spec.base_error_pct
        excess = max(0.0, err - max(base_err, spec.slo_error_pct))
        failed = rps * (excess / 100.0) * dur_min * 60.0
        rev = failed * REVENUE_PER_REQ.get(sid, 0.0)
        slow = 1.0 if p95 > spec.slo_p95_ms else 0.0
        budget_burn = (dur_min / MONTHLY_BUDGET_MIN) * 100.0 if (excess > 0 or slow) else 0.0
        if excess > 0 or slow:
            revenue += rev
            if sid in REVENUE_PER_REQ:
                users += failed / ASSUMED_SESSION_REQS
            rows.append({
                "service": sid, "error_rate_pct": round(err, 3),
                "slo_error_pct": spec.slo_error_pct, "p95_ms": round(p95, 1),
                "slo_p95_ms": spec.slo_p95_ms,
                "slo_status": "breaching" if (excess > 0 or slow) else "at_risk",
                "failed_requests": int(failed),
                "revenue_at_risk_usd": round(rev, 2),
                "error_budget_burn_pct": round(budget_burn, 3),
            })

    rows.sort(key=lambda r: -r["revenue_at_risk_usd"])
    breaching = [r["service"] for r in rows if r["slo_status"] == "breaching"]
    sev = ("SEV1" if revenue > 400 or "payment-service" in breaching or len(breaching) >= 4
           else "SEV2" if revenue > 40 or len(breaching) >= 2 else "SEV3")
    return {
        "severity": sev,
        "duration_min": round(dur_min, 2),
        "revenue_at_risk_usd": round(revenue, 2),
        "affected_users_est": int(users),
        "breaching_slos": breaching,
        "blast_radius": sorted(dependents_transitive(blame["leader"])),
        "per_service": rows,
        "assumptions": {
            "revenue_per_request_usd": REVENUE_PER_REQ,
            "requests_per_session": ASSUMED_SESSION_REQS,
            "note": "Monetary figures are derived from stated per-request "
                    "revenue assumptions applied to measured excess error "
                    "volume. They are an estimate, not a measurement.",
        },
        "provenance": "REAL (computation) over SIMULATED telemetry",
    }
