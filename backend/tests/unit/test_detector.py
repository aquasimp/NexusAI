"""Unit tests for multi-signal anomaly detection pipeline."""
import numpy as np
import pytest
from nexus.ml.detector import Detector
from nexus.simulation.engine import Engine
from nexus.simulation.scenarios import arm
from nexus.simulation.topology import METRICS, SERVICES

def test_detector_fit_and_inference():
    """Verify that detector fits cleanly on history and scores new frames."""
    e = Engine(seed=777)
    times, hist = [], {s: {m: [] for m in METRICS} for s in SERVICES}
    for _ in range(600):
        times.append(e.sim_time())
        f = e.tick()
        for s in SERVICES:
            for m in METRICS:
                hist[s][m].append(f[s][m])

    det = Detector(harmonics=2, quantile=0.99, persist_k=2, persist_n=4)
    det.fit(np.array(times), {s: {m: np.array(v) for m, v in d.items()} for s, d in hist.items()})

    assert det.fitted is True
    assert det.threshold > 0.0

    st = det.new_state()
    f_clean = e.tick()
    res_clean = det.score_frame(st, e.sim_time(), f_clean)
    assert "system_score" in res_clean
    assert "firing" in res_clean
    assert "services" in res_clean
    assert len(res_clean["services"]) == len(SERVICES)

def test_detector_detects_injected_fault():
    """Verify detector triggers when an intense fault is active."""
    e = Engine(seed=101)
    times, hist = [], {s: {m: [] for m in METRICS} for s in SERVICES}
    for _ in range(600):
        times.append(e.sim_time())
        f = e.tick()
        for s in SERVICES:
            for m in METRICS:
                hist[s][m].append(f[s][m])

    det = Detector(harmonics=2, quantile=0.95, persist_k=2, persist_n=4).fit(
        np.array(times), {s: {m: np.array(v) for m, v in d.items()} for s, d in hist.items()}
    )

    e2 = Engine(seed=500)
    st = det.new_state()
    arm(e2, "db_latency_spike")
    triggered = False
    for _ in range(50):
        ts = e2.sim_time()
        fr = e2.tick()
        score = det.score_frame(st, ts, fr)
        if score["firing"]:
            triggered = True
            break
    assert triggered is True
