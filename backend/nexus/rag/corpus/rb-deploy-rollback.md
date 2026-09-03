---
id: rb-deploy-rollback
title: Runbook — Rolling back a bad deployment
tags:
  - deploy
  - rollback
  - regression
  - release
services:
  - payment-service
  - api-gateway
  - auth-service
actions:
  - id: rollback_deploy; label: Roll back to previous release; risk: medium; reversible: true; blast_radius: single-service; expected: error rate and p95 return to pre-deploy baseline within 3 min
---

## Symptoms
A step change — not a ramp — in error rate and/or p95 aligned within one or two
evaluation windows of a rollout. Metrics from before the rollout are the control
group; if the shift coincides with the deploy marker and no dependency moved
first, the release is the prime suspect.

## Diagnosis
Compare the pre/post windows around the deploy marker for the deployed service
and confirm its dependencies did NOT degrade earlier. If a dependency moved
first, the deploy is a coincidence and rolling back will not recover the system.

## Remediation
`kubectl rollout undo deploy/<svc>` or re-pin the previous image tag. Roll back
before debugging: mean-time-to-innocence matters less than mean-time-to-recovery.
Preserve one pod of the bad revision for post-mortem heap and log capture.

## Verification
Error rate inside SLO, p95 within 10% of the pre-deploy baseline, and no
regression in downstream services for five minutes.
