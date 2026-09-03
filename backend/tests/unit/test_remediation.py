"""Unit tests for remediation planning and safety gating rules."""
import pytest
from nexus.agent.remediation import plan, retrieve_for_class


def _make_candidate(action_id="test_act", risk="low", reversible=True, blast_radius="single-instance"):
    return {
        "doc_id": "rb-test",
        "title": "Test Runbook",
        "actions": [{
            "id": action_id,
            "label": "Test Action",
            "risk": risk,
            "reversible": str(reversible).lower(),
            "blast_radius": blast_radius,
            "expected": "recovery",
        }],
    }


@pytest.mark.parametrize("risk,reversible,blast_radius,severity,expected_approval", [
    ("low", True, "single-instance", "SEV3", False),     # Safe low-risk action
    ("medium", True, "single-instance", "SEV3", True),   # Medium risk -> approval required
    ("high", True, "single-instance", "SEV3", True),     # High risk -> approval required
    ("low", False, "single-instance", "SEV3", True),    # Irreversible -> approval required
    ("low", True, "all-users", "SEV3", True),           # All-users blast radius -> approval required
    ("low", True, "multi-service", "SEV3", True),       # Multi-service blast radius -> approval required
    ("low", True, "single-instance", "SEV1", True),     # SEV1 severity -> approval required
])
def test_remediation_approval_policy_boundaries(risk, reversible, blast_radius, severity, expected_approval):
    """Verify exact safety-policy gates for automated vs human-approved execution."""
    doc = _make_candidate(risk=risk, reversible=reversible, blast_radius=blast_radius)
    impact = {"severity": severity, "revenue_at_risk_usd": 10.0}
    res = plan("bad_deploy", "payment-service", impact, [doc])

    rec = res["recommended"]
    assert rec["approval_required"] is expected_approval
    assert res["policy"]["auto_execute_allowed"] is (not expected_approval)


def test_remediation_fallback_when_no_candidates():
    """Verify fallback to no_op_observe when retrieved runbooks have no valid actions."""
    impact = {"severity": "SEV2", "revenue_at_risk_usd": 50.0}
    empty_doc = {"doc_id": "rb-empty", "title": "Empty", "actions": []}
    res = plan("unknown_class", "api-gateway", impact, [empty_doc])

    assert res["recommended"]["action_id"] == "no_op_observe"
    assert res["recommended"]["source_doc"] == "policy-default"


def test_retrieve_for_class_returns_valid_playbook():
    """Verify runbook retrieval for known RCA classes returns valid documents."""
    docs = retrieve_for_class("db_latency_saturation", ["postgres-primary"], k=2)
    assert len(docs) > 0
    assert any("postgres" in d["doc_id"] or "connection" in d["doc_id"] for d in docs)
