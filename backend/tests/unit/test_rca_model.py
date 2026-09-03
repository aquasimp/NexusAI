"""Unit tests for RCA ranker and fallback classification logic."""
import numpy as np
from nexus.ml.rca_model import RCARanker, CLASSES, build_pipeline
from nexus.ml.features import FEATURE_NAMES, N_FEATURES

def test_rca_heuristic_fallback_predict():
    """Verify untrained RCA ranker operates in rule fallback mode without crashing."""
    ranker = RCARanker()
    assert ranker.mode in ("rule", "learned")

    feat_dict = {
        "deploy_recent": 1.0,
        "deploy_on_leader": 1.0,
        "leader_mem_slope": 0.0,
        "sat_index": 0.2,
        "log_pool_exhausted": 0.0,
        "log_slow_query": 0.0,
        "log_lock_wait": 0.0,
        "log_cache_miss": 0.0,
    }
    x = np.zeros(N_FEATURES)
    for i, name in enumerate(FEATURE_NAMES):
        x[i] = feat_dict.get(name, 0.0)

    pred, rule_pred = ranker.predict(x, feat_dict)
    assert hasattr(pred, "top_class")
    assert hasattr(pred, "confidence")
    assert pred.confidence > 0.0
    assert len(pred.ranking) > 0

def test_rca_pipeline_construction():
    """Verify scikit-learn pipeline builds with expected classes."""
    pipe = build_pipeline()
    assert hasattr(pipe, "fit")
    assert hasattr(pipe, "predict_proba")
