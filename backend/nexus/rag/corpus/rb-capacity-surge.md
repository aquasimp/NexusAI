---
id: rb-capacity-surge
title: Runbook — Traffic surge and the queueing knee
tags:
  - capacity
  - scaling
  - surge
  - utilization
services:
  - api-gateway
  - auth-service
  - recommendation-service
actions:
  - id: scale_out; label: Double replicas on the saturated tier; risk: low; reversible: true; blast_radius: single-service; expected: utilization below 0.7 and p95 recovery within 2 min
  - id: throttle_ingress; label: Shed non-critical ingress at the edge; risk: high; reversible: true; blast_radius: all-users; expected: immediate relief, rejects some traffic
---

## Symptoms
Request volume well above the seasonal baseline, utilization above ~0.85, and
latency rising super-linearly while errors stay comparatively modest. Under
M/M/1 queueing, delay scales as 1/(1-u), so p95 roughly doubles between u=0.5
and u=0.75 and explodes past u=0.9 — a latency spike with proportional RPS
growth is capacity, not a defect.

## Diagnosis
Confirm the surge is real ingress rather than retry amplification from a failing
dependency: retry-driven load shows a failing downstream service with an
*earlier* onset.

## Remediation
Scale the saturated tier first, then re-check whether the next tier down has
become the new constraint. Load shedding is the emergency lever and requires
incident-commander approval because it rejects real user traffic.

## Verification
Utilization under 0.7 across the affected tier and p95 inside SLO.
