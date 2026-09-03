---
id: rb-postgres-latency
title: Runbook — Postgres primary latency & lock contention
tags:
  - postgres
  - latency
  - locks
  - saturation
services:
  - postgres-primary
  - payment-service
  - auth-service
actions:
  - id: kill_blocking_queries; label: Terminate blocking queries; risk: medium; reversible: true; blast_radius: single-service; expected: p95 returns to <60ms within 2 min
  - id: no_op_observe; label: Observe for 5 minutes; risk: none; reversible: true; blast_radius: none; expected: no change
---

## Symptoms
Primary p95 above 60ms for more than 3 consecutive minutes, `lock_wait` and
`duration:` slow-query lines in the log stream, and connection pool waiters
climbing on every caller. Latency inflation appears on the datastore FIRST and
on application services only afterwards — the onset ordering is the decisive
discriminator against an application-side regression.

## Diagnosis
Query `pg_stat_activity` for `wait_event_type = 'Lock'` and any transaction with
`state = 'idle in transaction'` older than 60s. A single long analytics
transaction holding `orders_pk` will serialise writers without raising CPU much,
so CPU-normal + latency-high + no recent deploy is the canonical signature.

## Remediation
Terminate the blocking backend with `pg_terminate_backend(pid)`. This is
medium-risk and reversible in effect but will roll back the offending
transaction, so confirm it is not a settlement job. Do NOT restart the primary;
failover multiplies the blast radius.

## Verification
p95 under 60ms, pool waiters at zero, caller error rate back inside SLO for two
consecutive evaluation windows before closing.
