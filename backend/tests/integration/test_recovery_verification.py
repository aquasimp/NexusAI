"""Integration test for remediation recovery verification and negative escalation path."""
from nexus.simulation.engine import Engine
from nexus.simulation.scenarios import arm


def test_recovery_verification_fails_on_wrong_action():
    """Verify that applying an ineffective mitigation does not lower latency and leaves fault active."""
    eng = Engine(seed=711)
    for _ in range(50):
        eng.tick()

    base_lat = eng.last_frame["postgres-primary"]["latency_p95"]

    # Inject db_latency_spike
    arm(eng, "db_latency_spike")
    for _ in range(25):
        eng.tick()

    fault_lat = eng.last_frame["postgres-primary"]["latency_p95"]
    assert fault_lat > 2.0 * base_lat

    # Apply wrong mitigation: restart_workload on database does not clear row locks
    eng.apply_action("restart_workload", "postgres-primary")

    for _ in range(25):
        eng.tick()

    post_lat = eng.last_frame["postgres-primary"]["latency_p95"]
    # Still elevated — wrong action did not clear the fault
    assert post_lat > 1.5 * base_lat


def test_recovery_verification_succeeds_on_gold_action():
    """Verify that applying the gold action restores telemetry within recovery window."""
    eng = Engine(seed=711)
    for _ in range(50):
        eng.tick()

    base_lat = eng.last_frame["postgres-primary"]["latency_p95"]
    arm(eng, "db_latency_spike")
    for _ in range(25):
        eng.tick()

    eng.apply_action("kill_blocking_queries", "postgres-primary")
    for _ in range(30):
        eng.tick()

    recovered_lat = eng.last_frame["postgres-primary"]["latency_p95"]
    assert recovered_lat < 0.6 * eng.last_frame["postgres-primary"]["latency_p95"] or recovered_lat < 2.0 * base_lat
