---
id: rb-redis-eviction
title: Runbook — Redis eviction storm and cascade containment
tags:
  - redis
  - cache
  - eviction
  - cascade
services:
  - redis-cache
  - auth-service
  - recommendation-service
  - notification-service
actions:
  - id: flush_and_warm_cache; label: Raise maxmemory and warm the working set; risk: medium; reversible: false; blast_radius: multi-service; expected: miss ratio below 10% and dependent latency recovery within 3 min
  - id: enable_fallback_cache; label: Enable local fallback caches on callers; risk: low; reversible: true; blast_radius: feature-degraded; expected: contains the cascade while the cache recovers
---

## Symptoms
Cache miss ratio climbing, then simultaneous-looking degradation across every
service that reads the cache, then edge saturation. Onset times are *staggered*
by dependency depth even when the dashboard makes them look concurrent — that
stagger is how you find the origin.

## Diagnosis
A cache miss converts a sub-millisecond read into a datastore round trip, so
effective downstream load multiplies by the miss ratio. Combined with retries,
this is the classic metastable failure: the system will not self-heal after the
trigger is removed because the retry load has become the new trigger.

## Remediation
Contain first (fallback caches, breakers, shed retries), then repair the cache.
Warming the working set before removing containment prevents a second collapse.

## Verification
Miss ratio under 10%, dependent p95 inside SLO, and breakers closed again
without recurrence.
