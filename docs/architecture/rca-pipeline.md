# Root Cause Analysis (RCA) Pipeline

## Two-Tier Classification Architecture

The RCA module predicts the root-cause failure class and blame attribution:

```
[Window Metrics + Anomaly + Blame + Logs + Deploys]
                        |
            [35-Dimensional Feature Extractor]
                        |
          +-------------+-------------+
          |                           |
  (Artifact Exists)           (No Model Fitted)
          v                           v
  [Learned Logistic]          [Rule-Based Scorer]
  Balanced L2 Regularization  Sigmoid Feature Scoring
  StandardScaler              Transparent Evidence
          |                           |
          +-------------+-------------+
                        v
         [Ranked Hypotheses + Evidence]
```

### 1. 35-Dimensional Feature Representation
Features are strictly class-agnostic and service-anonymized:
- **Service Kind One-Hot** (5): edge, app, datastore, cache, external
- **Leader Peak Z-Scores** (6): rps, p50, p95, error_rate, cpu, mem
- **Trend & Changepoint Dynamics** (4): OLS slope and Mann-Kendall tau on memory and latency
- **System-Level Context** (12): anomalous fraction, onset spread, deploy proximity, error/latency dominance
- **Log Signatures** (8): timeout, lock_wait, oom, schema_reject, pool_exhausted, cache_miss, circuit_open, slow_query

### 2. Dual-Mode Fallback
- **Learned Mode**: $L_2$-regularized multinomial LogisticRegression trained across multi-seed simulation episodes. Provides feature contribution breakdown for top predictions.
- **Rule Fallback**: Sigmoid matching functions over critical features ensuring the platform operates reliably out-of-the-box before any offline model training has been conducted.
