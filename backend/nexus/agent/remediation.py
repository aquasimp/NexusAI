"""Remediation planning grounded in retrieved runbook `actions` front-matter,
with an explicit safety gate. Nothing is executed without policy evaluation,
and high-risk / irreversible / multi-service actions always require human
approval."""
from __future__ import annotations

from ..rag.store import KB

RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
CLASS_QUERY = {
    "db_latency_saturation": "postgres primary latency lock contention slow query pool",
    "bad_deploy": "roll back bad deployment step change error rate after release",
    "memory_leak": "memory leak OOM restart heap growth GC pressure",
    "traffic_surge": "traffic surge capacity scale out utilization queueing",
    "dependency_outage": "third party dependency outage circuit breaker timeouts",
    "api_error_explosion": "5xx error explosion flat latency config schema validation rollback",
    "cascading_failure": "redis eviction cascade containment retry amplification fallback",
}


def plan(rca_class: str, root_service: str, impact: dict,
         retrieved: list[dict]) -> dict:
    docs, seen = [], set()
    for r in retrieved:
        if r["doc_id"] not in seen:
            seen.add(r["doc_id"])
            docs.append(r)

    candidates = []
    for r in docs:
        for a in r.get("actions", []):
            if not a.get("id"):
                continue
            candidates.append({
                "action_id": a["id"], "label": a.get("label", a["id"]),
                "risk": a.get("risk", "medium").lower(),
                "reversible": str(a.get("reversible", "true")).lower() == "true",
                "blast_radius": a.get("blast_radius", "unknown"),
                "expected_effect": a.get("expected", ""),
                "source_doc": r["doc_id"], "source_title": r["title"],
                "retrieval_rank": docs.index(r) + 1,
            })
    if not candidates:
        candidates = [{"action_id": "no_op_observe", "label": "Observe only",
                       "risk": "none", "reversible": True, "blast_radius": "none",
                       "expected_effect": "no change", "source_doc": "policy-default",
                       "source_title": "Default policy", "retrieval_rank": 99}]

    def score(c):
        return (c["retrieval_rank"] * 2
                + RISK_ORDER.get(c["risk"], 2)
                + (0 if c["reversible"] else 2)
                + (1 if c["blast_radius"] in ("all-users", "multi-service") else 0)
                + (-3 if c["action_id"] != "no_op_observe" else 4))

    candidates.sort(key=score)
    for c in candidates:
        c["approval_required"] = (
            RISK_ORDER.get(c["risk"], 2) >= 2 or not c["reversible"]
            or c["blast_radius"] in ("all-users", "multi-service")
            or impact["severity"] == "SEV1")
        c["policy_reason"] = _reason(c, impact)
        c["target"] = root_service
    return {"recommended": candidates[0], "alternatives": candidates[1:4],
            "policy": {
                "auto_execute_allowed": not candidates[0]["approval_required"],
                "rules": ["risk>=medium requires approval",
                          "irreversible requires approval",
                          "blast_radius in {all-users, multi-service} requires approval",
                          "SEV1 always requires approval",
                          "execution is simulated against the environment model"],
            }}


def _reason(c, impact) -> str:
    bits = [f"risk={c['risk']}",
            "reversible" if c["reversible"] else "IRREVERSIBLE",
            f"blast_radius={c['blast_radius']}", f"severity={impact['severity']}"]
    return " · ".join(bits)


def retrieve_for_class(rca_class: str, services: list[str], k: int = 4) -> list[dict]:
    return KB.search(CLASS_QUERY.get(rca_class, rca_class), k=k, services=services)
