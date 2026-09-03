---
id: rb-circuit-breaker
title: Standard — Circuit breakers, retries and timeout budgets
tags:
  - resilience
  - retries
  - circuit-breaker
  - timeouts
services:
  - api-gateway
  - payment-service
  - notification-service
actions:
  - id: enable_circuit_breaker; label: Open breaker on the failing edge; risk: medium; reversible: true; blast_radius: feature-degraded; expected: fail-fast instead of thread-pool exhaustion
---

## Symptoms
Retry amplification: downstream error rate rises and downstream *request rate*
rises with it, because every failure generates additional attempts.

## Diagnosis
Amplification factor equals one plus retries times failure probability. At a 50%
failure rate with two retries you are sending 2x the load into an already
failing dependency — the canonical way a small fault becomes an outage.

## Remediation
Open the breaker, cap retries at one with jittered exponential backoff, and
enforce a timeout budget that strictly decreases with call depth so an inner
call can never outlive its caller's deadline.

## Verification
Downstream request rate back to baseline and caller error rate inside SLO.
