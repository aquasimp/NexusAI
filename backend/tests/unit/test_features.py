"""Unit tests for ML feature extraction."""
import numpy as np
from nexus.ml.features import extract, FEATURE_NAMES, N_FEATURES
from nexus.simulation.topology import SERVICES, METRICS

def test_feature_vector_dimension():
    """Verify extracted feature vector length matches N_FEATURES exactly."""
    assert len(FEATURE_NAMES) == N_FEATURES
    assert N_FEATURES == 35

    T = 60
    window = {
        "n": T,
        "t_start": 0,
        "raw": {s: {m: np.random.uniform(10, 50, T) for m in METRICS} for s in SERVICES},
        "z": {s: np.random.normal(0, 1, (T, len(METRICS))) for s in SERVICES},
    }
    anomaly = {"anomalous_fraction": 0.25}
    blame = {
        "leader": "postgres-primary",
        "onset_spread_s": 15.0,
        "ranking": [{"service": s, "onset_lead_s": 10.0} for s in SERVICES],
    }
    logs = [
        {"tick": 50, "service": "postgres-primary", "pattern": "slow_query", "level": "WARN"}
    ]
    deploys = []

    vec, feat_dict = extract(window, anomaly, blame, logs, deploys, tick_seconds=15.0)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (35,)
    assert len(feat_dict) == 35
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()
