"""Integration test for autonomous incident investigation orchestrator."""
from nexus.world import world
from nexus.agent.orchestrator import Investigation, STAGES

def test_investigation_stages_defined():
    """Verify all 15 operational stages are registered and uniquely keyed."""
    assert len(STAGES) == 15
    stage_ids = [s[0] for s in STAGES]
    assert "baseline" in stage_ids
    assert "localize_service" in stage_ids
    assert "root_cause_ranked" in stage_ids
    assert "remediation_proposed" in stage_ids
    assert "remediation_executing" in stage_ids
    assert "recovery_verified" in stage_ids
    assert len(stage_ids) == len(set(stage_ids))

def test_investigation_instantiation():
    """Verify an investigation instance initializes state correctly."""
    inv = Investigation(world, "INC-TEST-0001")
    assert inv.id == "INC-TEST-0001"
    assert inv.trace == []
    assert inv.tool_calls == []
    assert inv.approval is not None
