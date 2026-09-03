"""Unit tests for investigation tools execution and error handling."""
import numpy as np
from nexus.agent import tools
from nexus.simulation.topology import SERVICES, METRICS


def _sample_context():
    n = 60
    times = list(range(n))
    raw = {
        s: {m: np.linspace(10.0, 50.0, n) if m == "latency_p95" else np.full(n, 5.0)
            for m in METRICS}
        for s in SERVICES
    }
    zmat = {s: np.zeros((n, len(METRICS))) for s in SERVICES}
    window = {"n": n, "t_start": 0, "t_end": n - 1, "times": times, "raw": raw, "z": zmat}
    logs = [
        {"tick": 10, "sim_ts": 150.0, "service": "payment-service", "level": "ERROR",
         "pattern": "timeout", "message": "Downstream timeout calling postgres"},
        {"tick": 20, "sim_ts": 300.0, "service": "api-gateway", "level": "WARN",
         "pattern": "slow_query", "message": "Upstream slow query observed"},
    ]
    deploys = [{"tick": 5, "service": "payment-service", "version": "v1.1", "author": "dev",
                "change": "fix", "risk": "low"}]
    anomaly = {"services": {s: {"score": 0.5, "firing": False} for s in SERVICES}}
    blame = {"ranking": [{"service": "payment-service", "blame": 0.8}], "leader": "payment-service"}
    impact = {"severity": "SEV2", "revenue_at_risk_usd": 120.0}
    return {"window": window, "logs": logs, "deploys": deploys, "anomaly": anomaly,
            "blame": blame, "impact": impact, "now_tick": n - 1}


def test_unknown_tool_call_returns_error():
    """Verify calling an unregistered tool returns an error structure instead of raising."""
    ctx = _sample_context()
    res = tools.call(ctx, "non_existent_tool_xyz", {"foo": "bar"})
    assert res["ok"] is False
    assert res["error"] == "unknown_tool"
    assert res["tool"] == "non_existent_tool_xyz"


def test_compare_windows_statistical_evaluation():
    """Verify compare_windows computes Welch's t and shift shape properly."""
    ctx = _sample_context()
    res = tools.call(ctx, "compare_windows", {
        "service": "payment-service",
        "metric": "latency_p95",
        "pivot_tick": 30
    })
    assert res["ok"] is True
    data = res["result"]
    assert "welch_t" in data
    assert "shift_pct" in data
    assert data["shape"] in ("step", "ramp")
    assert data["pivot_tick"] == 30


def test_read_runbook_missing_doc():
    """Verify read_runbook handles non-existent document IDs gracefully."""
    ctx = _sample_context()
    res = tools.call(ctx, "read_runbook", {"doc_id": "rb-nonexistent-123"})
    assert res["ok"] is True
    assert "error" in res["result"]
    assert "unknown doc_id" in res["result"]["error"]


def test_search_logs_filtering():
    """Verify search_logs filters correctly by service and keyword."""
    ctx = _sample_context()
    # Filter by service
    res_svc = tools.call(ctx, "search_logs", {"service": "payment-service", "query": ""})
    assert res_svc["ok"] is True
    assert res_svc["result"]["total"] == 1

    # Filter by query
    res_q = tools.call(ctx, "search_logs", {"query": "timeout"})
    assert res_q["ok"] is True
    assert res_q["result"]["total"] == 1

    # Non-existent query
    res_none = tools.call(ctx, "search_logs", {"query": "non_existent_pattern_string"})
    assert res_none["ok"] is True
    assert res_none["result"]["total"] == 0
