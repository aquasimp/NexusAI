---
id: rb-memory-leak
title: Runbook — Memory leak and OOM restart loops
tags:
  - memory
  - oom
  - gc
  - leak
services:
  - recommendation-service
  - notification-service
actions:
  - id: restart_workload; label: Rolling restart to reclaim heap; risk: low; reversible: true; blast_radius: single-service; expected: memory returns to ~55% and GC-induced latency clears
  - id: scale_out; label: Scale out to dilute per-pod pressure; risk: low; reversible: true; blast_radius: single-service; expected: partial mitigation only
---

## Symptoms
Monotonic memory growth over tens of minutes with request volume flat, followed
by GC-pressure latency inflation above ~88% heap, then FATAL OOM lines and
sawtooth restarts. Monotonicity is the signature: a Mann-Kendall tau above ~0.6
on memory with a flat RPS trend distinguishes a leak from load-driven growth.

## Diagnosis
Capture a heap dump before restarting. Unbounded in-process caches without a
size or TTL bound are the most common cause; look for maps keyed by user or
request id.

## Remediation
Rolling restart reclaims heap and is low risk, but it is a mitigation, not a
fix — the leak will return. File a follow-up to bound the cache and set a
container memory limit with a headroom alert at 85%.

## Verification
Memory flat for 15 minutes post-restart and GC pause time back to baseline.
