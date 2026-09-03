# ADR-001: Causal Queueing Network vs. Scripted Telemetry

## Status
Accepted

## Context
Traditional incident response demos replay pre-recorded CSVs or follow static timelines. This prevents genuine root-cause localization testing because symptoms do not propagate through dependencies, retries do not cause emergent congestion, and remediation actions cannot dynamically alter the physical simulation state.

## Decision
Implement an open $M/M/1$-based discrete-time queueing network where:
1. Demand flows top-down from external ingress.
2. Latencies and queue saturation propagate bottom-up.
3. Faults are injected only at root services.
4. Cascades (e.g. retry storms, cache miss stampedes) emerge naturally.

## Consequences
- **Positive**: Validates closed-loop causal reasoning; remediation actions physically alter system health; reproducible across random seeds.
- **Negative**: Requires strict reverse-topological order calculations; simulation parameters must maintain stable queueing bounds.
