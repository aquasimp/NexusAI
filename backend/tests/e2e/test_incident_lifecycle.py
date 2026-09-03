"""End-to-end test simulating a complete incident detection and mitigation loop."""
import pytest
from nexus.simulation.engine import Engine
from nexus.simulation.scenarios import arm
from nexus.simulation.topology import SERVICES

def test_full_incident_mitigation_lifecycle():
    """Verify that an injected fault degrades services and the gold action restores them."""
    eng = Engine(seed=999)
    # Warm up 50 ticks
    for _ in range(50):
        eng.tick()

    baseline_latency = eng.last_frame["postgres-primary"]["latency_p95"]

    # Arm fault
    sc = arm(eng, "db_latency_spike")
    assert sc.root_service == "postgres-primary"

    # Propagate 20 ticks
    for _ in range(20):
        eng.tick()

    fault_latency = eng.last_frame["postgres-primary"]["latency_p95"]
    assert fault_latency > baseline_latency

    # Apply gold action
    eng.apply_action("kill_blocking_queries", "postgres-primary")

    # Run 30 ticks to recover
    for _ in range(30):
        eng.tick()

    recovered_latency = eng.last_frame["postgres-primary"]["latency_p95"]
    assert recovered_latency < 0.6 * fault_latency
