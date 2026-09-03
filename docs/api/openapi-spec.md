# NEXUS AI REST & Real-time API Specification

## Base URL
`http://localhost:8000/api`

## Core Endpoints

### Health & System Status
- `GET /health`: Returns engine tick, running state, and overall health score.
- `GET /system/info`: Returns simulation configuration, LLM mode, RCA ranker status, and provenance mappings.

### Topology & Telemetry
- `GET /topology`: Returns all 9 microservices, dependencies, SLOs, and capacities.
- `GET /series?ticks=180`: Time series telemetry arrays for all services and metrics.
- `GET /logs?limit=200&service=...`: Structured log stream with level filtering.
- `GET /deploys`: History of container deployments and configuration changes.

### Real-Time Streaming
- `GET /live/stream`: Server-Sent Events (SSE) emitting:
  - `tick`: Per-tick telemetry snapshot, health scores, and anomaly firing state.
  - `incident_opened`: Broadcasts when a multi-metric anomaly is detected.
  - `stage`: Real-time progress updates across the 15 investigation stages.
  - `incident_closed`: Emitted upon verified remediation.

### Incident Management & Simulation
- `POST /simulate`: Trigger an incident scenario (`db_latency_spike`, `bad_deploy`, `memory_leak`, `cascading_failure`, `api_error_explosion`, `dependency_outage`, `traffic_surge`, or `random`).
- `POST /reset`: Reinitializes engine clock, clears incident journals, and runs 90 warm-up ticks.
- `GET /incidents`: Returns list of past and active incident records.
- `GET /incidents/{iid}`: Retrieves complete investigation trace, tool calls, and stage timeline.
- `POST /incidents/{iid}/approve`: Submits human operator approval or rejection for proposed remediation.

### Knowledge Base & Evaluation
- `GET /kb/search?q=...&k=5`: Hybrid BM25 + SVD search over operational runbooks.
- `GET /kb/docs`: Lists all indexed runbooks.
- `GET /evaluation`: Retrieves latest benchmark results with Wilson confidence intervals.
- `POST /evaluation/run`: Triggers a background benchmark execution across multiple seeds.
