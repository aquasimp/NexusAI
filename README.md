# NEXUS AI

> **Autonomous Incident Intelligence Platform over Causal Telemetry Simulation**

[![Backend CI](https://github.com/aquasimp/NexusAI/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Frontend CI](https://github.com/aquasimp/NexusAI/actions/workflows/frontend.yml/badge.svg)](.github/workflows/frontend.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/next.js-16.3-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.1-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

NEXUS AI is a production-oriented autonomous Site Reliability Engineering (SRE) intelligence platform prototype. It couples a closed-loop causal telemetry simulation engine with a multi-stage machine learning and LLM reasoning pipeline to automatically detect, isolate, diagnose, and remediate distributed microservice failures.

Everything runs **completely offline** with zero API keys required by default.

---

## Architecture Overview

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

---

## Key Capabilities

1. **Causal Queueing Network Simulation**:
   - 9 microservices across 4 tiers / 5 service kinds (Edge, Application, Datastores, In-Memory Caches, External SaaS).
   - Diurnal sinusoidal traffic curves with Poisson arrivals.
   - Emergent cascades: retry storms, queue saturation, and downstream backpressure emerge causally rather than following hardcoded scripts.
2. **Multi-Signal Statistical Anomaly Detection**:
   - Fourier harmonic baseline removal ($H=3$) models diurnal patterns.
   - Lag-1 AR(1) whitening of residuals to produce i.i.d. innovations.
   - Fused Ledoit-Wolf Mahalanobis distance and IsolationForest for multi-dimensional anomaly detection.
3. **35-Dimensional RCA Classification**:
   - Strict service anonymization and class-agnostic features prevent label memorization.
   - Dual-mode operation: $L_2$-regularized multinomial LogisticRegression with feature contribution attribution, plus deterministic rule fallback.
4. **Sub-Second Hybrid Runbook RAG**:
   - 10 standard SRE incident runbooks indexed in memory.
   - Pure-Python BM25 lexical search fused with 16-dimensional Latent Semantic Analysis (TF-IDF + SVD) via Reciprocal Rank Fusion (RRF).
5. **15-Stage Autonomous Incident Orchestrator**:
   - Closed-loop investigation from triage, localization, log correlation, hypothesis generation, and impact estimation to remediation and post-mitigation verification.
   - Policy guard with human operator approval gating for high-risk actions on Tier-0/1 services.
6. **Auditable Benchmark Harness**:
   - Multi-episode evaluation across 7 failure scenarios and 24 clean baseline episodes.
   - Reports Precision, Recall, Specificity, F1, Detection Delay, Top-k Localization, and MTTR with 95% Wilson score confidence intervals. No hardcoded or fabricated numbers.

---

## Repository Structure

```
nexusAI/
├── .github/
│   └── workflows/              # GitHub Actions CI for backend and frontend
├── backend/
│   ├── nexus/
│   │   ├── config/             # Pydantic v2 BaseSettings configuration
│   │   ├── core/               # Logging, domain exceptions, cross-cutting concerns
│   │   ├── api/                # FastAPI REST router and Pydantic schemas
│   │   ├── realtime/           # Server-Sent Events (SSE) broadcasting hub
│   │   ├── persistence/        # SQLite incident and evaluation journal
│   │   ├── simulation/         # Queueing network, microservice topology, scenarios
│   │   ├── ml/                 # Harmonic baselines, detector, CUSUM, features, RCA
│   │   ├── rag/                # Runbook corpus and BM25+SVD hybrid retrieval
│   │   ├── agent/              # 15-stage orchestrator, tools, remediation, LLM
│   │   ├── evaluation/         # Multi-episode benchmark harness and Wilson CIs
│   │   ├── main.py             # FastAPI entrypoint application
│   │   └── world.py            # Global background execution loop and state singleton
│   ├── tests/
│   │   ├── conftest.py         # Pytest test fixtures
│   │   ├── unit/               # Unit test suites (detector, features, RCA, RAG, etc.)
│   │   ├── integration/        # API and agent integration tests
│   │   └── e2e/                # End-to-end incident mitigation lifecycle test
│   ├── pyproject.toml          # PEP 517/621 package and pytest configuration
│   ├── requirements.txt        # Production dependencies
│   └── Dockerfile              # Backend container build
├── web/
│   ├── app/                    # Next.js 16 App Router pages
│   │   ├── (shell)/            # Command Center, Investigation, Topology Map, Eval
│   │   ├── globals.css         # Tailwind v4 dark-mode design system
│   │   └── layout.tsx          # Root HTML layout and font definitions
│   ├── components/             # Reusable UI, topology graph, timeline components
│   ├── lib/                    # API client, SSE subscriber, TypeScript types
│   ├── package.json            # Node.js dependencies
│   └── Dockerfile              # Frontend container build
├── docs/
│   ├── architecture/           # System, simulator, ML, and RAG deep-dives
│   ├── decisions/              # Architecture Decision Records (ADR 001 - 004)
│   ├── api/                    # OpenAPI endpoint specifications
│   ├── ml/                     # 35-feature dictionary
│   └── evaluation/             # Benchmark methodology and metric definitions
├── scripts/
│   ├── setup/                  # Developer setup and package initialization
│   ├── benchmark/              # Benchmark execution CLI
│   └── development/            # Concurrent backend/web development runner
├── data/                       # Local SQLite database, model weights, eval results
├── docker-compose.yml          # Multi-container local orchestration
├── Makefile                    # Standard developer automation targets
├── CONTRIBUTING.md             # Engineering team guidelines
└── LICENSE                     # MIT License
```

---

## Quickstart

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 20 or higher
- **Git**

### 1. Automated Setup
```bash
# Clone the repository
git clone https://github.com/aquasimp/NexusAI.git
cd NexusAI

# Run the one-command setup
python scripts/setup/setup.py
# or using Make:
make setup
```

### 2. Start Local Development
```bash
make dev
# or:
python scripts/development/run_dev.py
```
- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 3. Run with Docker Compose
```bash
docker-compose up --build
```

---

## Testing & Quality Assurance

### Run Backend Test Suite
```bash
make test
# or:
cd backend && pytest tests/unit tests/integration tests/e2e -v
```

### Run Frontend Static Checks
```bash
cd web
npm run typecheck
npm run build
```

### Run Benchmark Harness
```bash
# Quick smoke benchmark (1 clean episode, 1 seed per scenario):
make quick

# Full rigorous scientific benchmark:
make eval
```

---

## Honesty & Provenance Labels

Every metric, calculation, and UI component carries explicit provenance:
- **`REAL`**: Authentic computation (statistical models, covariance shrinkage, rankers, optimization, benchmarks).
- **`SIMULATED`**: Synthetic generation representing physical infrastructure (telemetry queues, logs, deploy events).
- **`PRODUCTION-GAP`**: Real-world components that would replace simulated parts in a multi-region deployment (e.g. OpenTelemetry collector, Kafka, external Vector DB).

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
