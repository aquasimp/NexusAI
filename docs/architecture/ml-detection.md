# Multi-Signal Statistical Anomaly Detection

## Philosophy: Statistical Rigor Over Naive Thresholds

Static thresholding ($p95 > 500\text{ms}$) fails in production because normal baseline telemetry exhibits strong diurnal cycles (peak hours vs. off-peak hours). NEXUS uses a three-tier statistical detection architecture:

### 1. Harmonic Baseline Decomposition
Normal metric behavior is modeled as a Fourier expansion of time-of-day:
$$\hat{y}(t) = \beta_0 + \sum_{k=1}^{H} \left(\beta_{1k} \sin(2\pi k \cdot \text{tod}) + \beta_{2k} \cos(2\pi k \cdot \text{tod})\right)$$
where $H=3$ harmonics by default.

### 2. AR(1) Whitening
Residuals $\epsilon(t) = y(t) - \hat{y}(t)$ exhibit temporal autocorrelation. We whiten the series using estimated lag-1 autocorrelation:
$$\tilde{\epsilon}(t) = \epsilon(t) - \rho \epsilon(t-1)$$
producing independent and identically distributed (i.i.d.) innovations.

### 3. Fused Multivariate Distance
For each service across all 6 telemetry metrics ($rps, p50, p95, \text{error\_rate}, cpu, mem$), we compute two complementary anomaly signals:
- **Ledoit-Wolf Regularized Mahalanobis Distance**: Sensitive to linear metric covariance breakdown.
- **Isolation Forest**: Sensitive to non-linear multi-dimensional outliers.

The percentiles of both methods are rank-fused. System-level anomaly firing requires $k=3$ anomalous evaluations out of $n=5$ consecutive ticks to eliminate false alarms.
