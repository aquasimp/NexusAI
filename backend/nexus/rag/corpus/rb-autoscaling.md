---
id: rb-autoscaling
title: Standard — Autoscaling policy and safe scale-out
tags:
  - autoscaling
  - hpa
  - capacity
  - policy
services:
  - api-gateway
  - auth-service
  - recommendation-service
actions:
  - id: scale_out; label: Manual scale-out override; risk: low; reversible: true; blast_radius: single-service; expected: utilization relief within 90s
---

## Symptoms
Utilization sustained above target while replica count is pinned — HPA at its
`maxReplicas` ceiling, blocked on quota, or oscillating because the scaling
metric is latency (which is an outcome, not a cause).

## Diagnosis
Scale on utilization or concurrency, never on latency: latency-driven HPAs
amplify the very oscillation they are trying to damp. Check quota and node
headroom before assuming the policy is wrong.

## Remediation
Manual override to double replicas, then raise `maxReplicas` with headroom for
2x the observed peak. Verify the next tier down can absorb the additional
concurrency before scaling out the tier above it.

## Verification
Utilization at target, no scaling oscillation across three cycles.
