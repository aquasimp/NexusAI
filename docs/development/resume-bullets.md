## 6. Resume bullets

**Built NEXUS AI, an autonomous incident-intelligence platform** (Next.js 16/TypeScript + FastAPI/Python) that detects anomalies in live multi-service telemetry, localizes the originating fault across a dependency graph, ranks root causes with evidence, and proposes runbook-grounded remediation behind a policy-driven human-approval gate — end-to-end investigation latency measured in single-digit milliseconds excluding LLM narration.

**Engineered the ML detection and diagnosis pipeline from first principles:** harmonic seasonal regression with AR(1) residual whitening and MAD scaling, fused Ledoit-Wolf-shrinkage Mahalanobis and IsolationForest scoring with a k-of-n persistence gate, CUSUM changepoint onset ordering, dependency-graph blame propagation, and a 30-feature multinomial-logistic root-cause classifier validated with GroupKFold cross-validation and Wilson confidence intervals.

**Designed the evaluation harness that governs the project's own claims:** a causal queueing-network simulator generates labelled incident episodes replayed through the production code path to compute detection F1/PR-AUC, localization top-k, root-cause accuracy/macro-F1, retrieval recall/MRR/nDCG, and joint end-to-end success — every metric in the UI is computed at run time, with no hard-coded numbers anywhere in the repository.

*(Swap the third bullet for a RAG-specific one if the role is AI-engineering: "Implemented hybrid BM25 + TF-IDF/SVD retrieval with reciprocal rank fusion over an engineering runbook corpus, grounding an eight-tool agentic investigation loop whose recommended actions are drawn only from retrieved documents, with per-claim citations surfaced in the UI.")*

---
