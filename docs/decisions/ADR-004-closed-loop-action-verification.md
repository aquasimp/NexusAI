# ADR-004: Closed-Loop Action Verification and Human Approval Gating

## Status
Accepted

## Context
Automated remediation in production environments presents catastrophic risk if the agent executes arbitrary shell commands or restarts critical stateful datastores without verification.

## Decision
1. **Curated Remediation Actions**: Actions are discrete, whitelisted operational primitives (`restart_workload`, `rollback_deploy`, `kill_blocking_queries`, `scale_replicas`, `enable_circuit_breaker`, `enable_fallback_cache`).
2. **Policy Guard & Human Approval**: Destructive actions on Tier-0/1 services require an explicit operator approval event via API/UI or trigger an emergency review gate.
3. **Closed-Loop Verification**: After an action is applied, the agent does not declare victory immediately. It monitors subsequent simulation ticks to measure latency reduction, error drop, and health recovery before closing the incident.

## Consequences
- **Positive**: Eliminates rogue agent actions; guarantees that recovery is statistically confirmed before marking an incident resolved.
- **Negative**: Adds verification tick delays to MTTR measurement.
