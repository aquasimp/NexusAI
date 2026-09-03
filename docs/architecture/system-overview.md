# NEXUS AI System Architecture

## Executive Overview

**NEXUS AI** is an enterprise-grade autonomous Site Reliability Engineering (SRE) intelligence platform. It couples a closed-loop causal telemetry simulation engine with a multi-stage machine learning and LLM reasoning pipeline to automatically detect, isolate, diagnose, and remediate distributed microservice failures.

```
+-------------------------------------------------------------------------+
|                               Web UI                                    |
|   Next.js 16 - React 19 - Server-Sent Events (SSE) - Topological Graph  |
+-------------------------------------------------------------------------+
                                    | HTTP / SSE
+-------------------------------------------------------------------------+
|                              FastAPI API                                |
|   /api/live/stream  |  /api/incidents  |  /api/simulate  |  /api/kb     |
+-------------------------------------------------------------------------+
         |                                                 |
+-------------------+                             +-----------------------+
|  Real-time World  |                             |  Incident Pipeline    |
|  - Engine Loop    |<----+                       |  1. Anomaly Detection |
|  - SSE Hub        |     | Mitigation Loop       |  2. Root Localization |
|  - Event Journal  |     |                       |  3. RCA Classifier    |
+-------------------+     |                       |  4. Hybrid RAG (KB)   |
         |                |                       |  5. LLM Synthesis     |
+-------------------+     |                       |  6. Policy Guard      |
| Causal Simulator  |-----+                       |  7. Human-in-the-Loop |
| - M/M/1 Queues    |                             |  8. Action & Verify   |
| - Diurnal Traffic |                             +-----------------------+
| - Fault Injection |
+-------------------+
```

## Architectural Pillars

### 1. Honest Provenance Model
Every UI component, metric, and investigation step carries an explicit provenance tag:
- `REAL`: Authentic statistical models, Ledoit-Wolf covariance shrinkage, IsolationForest, OLS/Mann-Kendall trend estimators, scikit-learn LogisticRegression, BM25 + SVD hybrid retrieval, and Wilson score intervals.
- `SIMULATED`: Real-time queueing network simulating 9 microservices, Poisson arrivals, diurnal curves, cascading retries, connection pool exhaustion, memory leaks, and distributed tracing spans.
- `PRODUCTION-GAP`: Real-world infrastructure components (such as OpenTelemetry collectors, Kafka message brokers, and enterprise vector databases) that would replace simulated components in a multi-region deployment.

### 2. Microservice Topology
The simulated architecture reflects a real-world enterprise e-commerce platform across 4 tiers / 5 service kinds:
1. **Tier 0 (Edge)**: `api-gateway` (FastAPI/Envoy proxy)
2. **Tier 1 (Application)**: `auth-service`, `payment-service`, `recommendation-service`, `notification-service`
3. **Tier 2 (Datastore / Cache)**: `postgres-primary`, `redis-cache`
4. **Tier 3 (External SaaS)**: `stripe-api`, `sendgrid-api`
