---
id: rb-error-spike
title: Runbook — 5xx explosion with flat latency
tags:
  - errors
  - 5xx
  - config
  - validation
services:
  - api-gateway
actions:
  - id: rollback_deploy; label: Roll back the config/route change; risk: medium; reversible: true; blast_radius: all-users; expected: 5xx rate returns to baseline within 1 min
---

## Symptoms
Error rate an order of magnitude above baseline while p95 latency, CPU and
memory remain at baseline. Fast failures mean requests are being *rejected*, not
*starved* — this rules out saturation and dependency latency and points at
validation, routing, authorization or feature-flag configuration.

## Diagnosis
Group 5xx by route and error class. `schema validation failed` concentrated on a
single field immediately after a config push is conclusive. Confirm downstream
services are healthy: a genuine dependency failure would also inflate latency.

## Remediation
Roll the config back. Because gateway configuration affects all users, treat it
as SEV1 and page the incident commander even though the fix is trivial.

## Verification
5xx inside SLO by route and synthetic checkout probe passing.
