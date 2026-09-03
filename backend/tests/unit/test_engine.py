import numpy as np
from nexus.ml.detector import Detector
from nexus.rag.store import KB
from nexus.sim.engine import Engine, Fault
from nexus.sim.scenarios import arm
from nexus.sim.topology import METRICS, SERVICES


def _run(e, n):
    out = []
    for _ in range(n):
        out.append(e.tick())
    return out


def test_deterministic_given_seed():
    a = _run(Engine(seed=42), 60)[-1]
    b = _run(Engine(seed=42), 60)[-1]
    assert a == b


def test_healthy_baseline_respects_slos():
    frames = _run(Engine(seed=3), 240)[-60:]
    for sid, spec in SERVICES.items():
        p95 = np.mean([f[sid]["latency_p95"] for f in frames])
        err = np.mean([f[sid]["error_rate"] for f in frames])
        assert p95 < spec.slo_p95_ms, (sid, p95)
        assert err < max(spec.slo_error_pct, 0.5), (sid, err)


def test_db_fault_propagates_to_callers_without_being_injected_there():
    e = Engine(seed=11)
    _run(e, 100)
    base = np.mean([f["payment-service"]["latency_p95"] for f in _run(e, 20)])
    arm(e, "db_latency_spike")
    after = np.mean([f["payment-service"]["latency_p95"] for f in _run(e, 40)][-15:])
    assert after > 2.0 * base            # causal propagation, not injection


def test_cascade_is_emergent_and_broad():
    e = Engine(seed=13)
    _run(e, 100)
    arm(e, "cascading_failure")
    f = _run(e, 60)[-1]
    hurt = [s for s, spec in SERVICES.items()
            if f[s]["latency_p95"] > 2 * spec.slo_p95_ms]
    assert "redis-cache" in hurt and len(hurt) >= 3


def test_remediation_actually_recovers_and_wrong_action_does_not():
    for action, should_recover in (("kill_blocking_queries", True),
                                   ("restart_workload", False)):
        e = Engine(seed=21)
        _run(e, 100)
        arm(e, "db_latency_spike")
        _run(e, 40)
        bad = np.mean([f["postgres-primary"]["latency_p95"] for f in _run(e, 5)])
        e.apply_action(action, "postgres-primary")
        end = np.mean([f["postgres-primary"]["latency_p95"] for f in _run(e, 40)][-10:])
        assert (end < 0.5 * bad) == should_recover, action


def test_detector_fires_on_incident_and_is_quiet_when_clean():
    e = Engine(seed=101)
    times, hist = [], {s: {m: [] for m in METRICS} for s in SERVICES}
    for _ in range(2400):
        times.append(e.sim_time())
        f = e.tick()
        for s in SERVICES:
            for m in METRICS:
                hist[s][m].append(f[s][m])
    det = Detector().fit(np.array(times),
                         {s: {m: np.array(v) for m, v in d.items()}
                          for s, d in hist.items()})
    e2, st = Engine(seed=55), det.new_state()
    quiet = 0
    for _ in range(120):
        quiet += bool(det.score_frame(st, e2.sim_time(), e2.tick())["firing"])
    assert quiet <= 3                                   # low false-positive rate
    arm(e2, "bad_deploy")
    fired = any(det.score_frame(st, e2.sim_time(), e2.tick())["firing"]
                for _ in range(40))
    assert fired


def test_retrieval_finds_gold_docs():
    top = [r["doc_id"] for r in KB.search(
        "postgres primary latency lock contention slow query", k=3)]
    assert "rb-postgres-latency" in top
    top = [r["doc_id"] for r in KB.search(
        "memory leak OOM heap growth restart", k=3)]
    assert "rb-memory-leak" in top
