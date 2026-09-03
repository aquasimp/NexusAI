---
id: rb-connection-pool
title: Runbook — Connection pool exhaustion
tags:
  - pool
  - hikari
  - saturation
  - database
services:
  - payment-service
  - auth-service
  - postgres-primary
actions:
  - id: kill_blocking_queries; label: Release the blocking backend holding pool connections; risk: medium; reversible: true; blast_radius: single-service; expected: waiters drain to zero
---

## Symptoms
`pool exhausted: active=N idle=0 waiting=M` with request latency pinned at
almost exactly the pool acquisition timeout. Latency looks bimodal: fast
cache-hit paths remain fine while database paths cliff.

## Diagnosis
Pool exhaustion is nearly always a *symptom* of downstream slowness — Little's
Law says required concurrency equals arrival rate times service time, so a 6x
service-time inflation exhausts any fixed pool. Fix the service time, not the
pool size, unless the pool is genuinely under-provisioned at baseline.

## Remediation
Resolve the downstream latency source. Raising `maximumPoolSize` under an
active incident usually deepens the queue and pushes the failure into the
database instead.

## Verification
Waiters at zero and acquisition p99 under 5ms.
