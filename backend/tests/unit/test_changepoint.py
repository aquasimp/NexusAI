"""Unit tests for CUSUM and trend analysis functions."""
import numpy as np
from nexus.ml.changepoint import cusum_onset, onset_for_service, trend_slope, mann_kendall_tau

def test_cusum_detects_step_change():
    """Verify two-sided CUSUM identifies onset index of a positive mean shift."""
    rng = np.random.default_rng(42)
    # Baseline noise around 0, then large shift to 4.0 at index 25
    series = np.concatenate([rng.normal(0, 0.3, 25), rng.normal(4.0, 0.3, 35)])
    onset = cusum_onset(series, drift=0.6, threshold=4.0)
    assert onset is not None
    assert 22 <= onset <= 28

def test_cusum_quiet_on_stationary_noise():
    """Verify CUSUM does not trigger on stationary white noise."""
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 0.5, 100)
    onset = cusum_onset(noise, drift=0.6, threshold=6.0)
    assert onset is None

def test_trend_slope_monotonic():
    """Verify OLS normalized trend slope is strongly positive for linear climb."""
    ramp = np.linspace(10, 100, 50)
    slope = trend_slope(ramp)
    assert slope > 0.05

def test_mann_kendall_tau():
    """Verify Mann-Kendall tau is close to 1.0 for strictly increasing monotonic signal."""
    ramp = np.arange(30, dtype=float)
    tau = mann_kendall_tau(ramp)
    assert abs(tau - 1.0) < 1e-4


def test_onset_for_service_finds_earliest_metric():
    """Verify onset_for_service finds the earliest changepoint across metrics."""
    z = np.zeros((50, 3))
    z[30:, 0] = 5.0  # shift at 30 for metric 0
    z[20:, 1] = 5.0  # earlier shift at 20 for metric 1
    onset = onset_for_service(z)
    assert onset is not None
    assert 18 <= onset <= 22
