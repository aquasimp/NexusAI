"""Two-sided CUSUM changepoint detection used to estimate incident onset t0."""
from __future__ import annotations
import numpy as np


def cusum_onset(z: np.ndarray, drift: float = 0.6, threshold: float = 6.0) -> int | None:
    """Return index of first sustained mean shift in a z-score series, else None."""
    if len(z) < 6:
        return None
    hi = lo = 0.0
    hi_start = lo_start = 0
    for i, v in enumerate(z):
        prev_hi, prev_lo = hi, lo
        hi = max(0.0, hi + v - drift)
        lo = max(0.0, lo - v - drift)
        if prev_hi == 0.0 and hi > 0.0:
            hi_start = i
        if prev_lo == 0.0 and lo > 0.0:
            lo_start = i
        if hi > threshold:
            return hi_start
        if lo > threshold:
            return lo_start
    return None


def onset_for_service(zmatrix: np.ndarray) -> int | None:
    """zmatrix: (T, n_metrics). Earliest changepoint across metrics."""
    cands = [c for c in (cusum_onset(zmatrix[:, j]) for j in range(zmatrix.shape[1]))
             if c is not None]
    return min(cands) if cands else None


def trend_slope(y: np.ndarray) -> float:
    """OLS slope per tick, normalised by series scale (monotonic-growth signal)."""
    if len(y) < 5:
        return 0.0
    t = np.arange(len(y), dtype=float)
    t -= t.mean()
    denom = float(np.std(y)) or 1.0
    return float((t @ (y - y.mean())) / (t @ t) / denom)


def mann_kendall_tau(y: np.ndarray) -> float:
    """Non-parametric monotonic trend strength in [-1, 1]."""
    n = len(y)
    if n < 4:
        return 0.0
    if n > 120:
        y = y[np.linspace(0, n - 1, 120).astype(int)]
        n = 120
    s = sum(np.sign(y[j] - y[i]).sum() for i, j in [(i, slice(i + 1, n)) for i in range(n - 1)])
    return float(s / (0.5 * n * (n - 1)))
