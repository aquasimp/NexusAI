# ADR-002: Statistical ML and Discriminative Models Before LLM Reasoning

## Status
Accepted

## Context
LLMs suffer from hallucinations, high latency, context limits, and poor quantitative reasoning over raw time-series arrays containing thousands of high-frequency data points.

## Decision
Use statistical and discriminative ML algorithms for detection, localization, changepoint estimation, and root-cause classification *before* involving an LLM:
1. **Harmonic + AR(1) whitening**: Normalizes cyclical baselines.
2. **Ledoit-Wolf Mahalanobis + Isolation Forest**: Detects multivariate anomalies.
3. **Two-sided CUSUM & OLS/Mann-Kendall**: Identifies onset timestamps and monotonic trends.
4. **Regularized Logistic Regression**: Computes class probabilities and feature contributions.
5. **LLM**: Acts strictly as the synthesis, critique, and natural-language communication layer.

## Consequences
- **Positive**: Platform operates at sub-second speeds completely offline; LLM receives grounded facts and evidence tokens rather than raw numbers; deterministic behavior is measurable via standard ML benchmarks.
- **Negative**: Feature extraction pipeline must be maintained and versioned.
