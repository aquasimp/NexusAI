---
id: rb-third-party-outage
title: Runbook — Third-party dependency outage
tags:
  - third-party
  - stripe
  - outage
  - timeout
services:
  - stripe-api
  - sendgrid-api
  - payment-service
  - notification-service
actions:
  - id: enable_circuit_breaker; label: Open circuit breaker on the failing dependency; risk: medium; reversible: true; blast_radius: feature-degraded; expected: caller error rate drops sharply, affected feature degrades gracefully
  - id: enable_fallback_cache; label: Serve last-known-good from fallback cache; risk: low; reversible: true; blast_radius: feature-degraded; expected: stale-but-available responses
---

## Symptoms
Near-total error rate confined to an external provider node, timeouts on its
direct callers, and healthy internals everywhere upstream of that call path.
Error share concentrated on an external node with no internal deploy is the
signature.

## Diagnosis
Check the provider status page and correlate. Critically: rolling back your own
release will not help and wastes the first ten minutes of the incident.

## Remediation
Open the breaker so callers fail fast instead of consuming their own thread
pools waiting on timeouts — an un-broken circuit converts a partner outage into
your own saturation incident. Queue writes for later replay where the operation
is idempotent.

## Verification
Caller error rate inside SLO with the feature explicitly marked degraded, and
breaker state observable in the dashboard.
