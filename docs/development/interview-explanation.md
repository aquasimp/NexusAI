## 7. Sixty-second interview explanation

"NEXUS is an autonomous incident-response system. It watches telemetry from a nine-service mesh, and when something breaks it does what an on-call engineer does: figures out which service is actually the cause, explains why, estimates the cost, and recommends the specific documented fix.

The part I'd want to highlight is the simulator, because it's what makes the rest testable. It's a queueing model, not a script. I inject exactly one root fault — say the database's service time goes up six times — and every other symptom is derived: payment's latency rises because latency is computed as service time over one minus utilization plus fan-out-weighted downstream latency; its error rate rises because timeout probability is a function of its own p95 against its configured timeout; and its retries push more load onto the database, which is a real feedback loop. So cascades emerge from the graph rather than from a timeline I wrote.

That gives me unlimited labelled episodes, which is what let me build a real evaluation harness. It replays those episodes through the exact production code path and measures detection F1, localization top-k, root-cause accuracy under seed-grouped cross-validation, retrieval nDCG, and joint end-to-end success. Every number in the UI comes out of that harness at run time — nothing is hard-coded.

On the AI side, I made a deliberate split: statistics decide, the LLM explains. Ranking is a logistic-regression classifier over thirty incident features that I can cross-validate. The LLM gets eight tools that read genuine state, an evidence packet, and permission to disagree with the ranking in writing. And after remediation, the detector independently re-checks recovery — if the action was wrong, the system doesn't recover and the incident escalates instead of closing."

---
