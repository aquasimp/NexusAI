# Runbook Retrieval Augmented Generation (RAG)

## Design: Fully Offline Hybrid Search

NEXUS contains an authentic knowledge base of 10 standard SRE operational runbooks (`rb-postgres-latency`, `rb-redis-eviction`, `rb-bad-deploy`, etc.) located in `backend/nexus/rag/corpus/`.

### Hybrid Retrieval Architecture
To ensure complete offline execution without external vector database dependencies or remote embedding APIs, NEXUS uses hybrid lexical-latent retrieval:

1. **BM25 Lexical Matching**:
   Captures exact technical identifiers, service names, error strings, and configuration parameters (`pg_stat_activity`, `maxmemory`, `pool_exhausted`).
   $$s_{\text{BM25}}(d, q) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, d) \cdot (k_1 + 1)}{f(t, d) + k_1 \cdot \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}$$
2. **TF-IDF + Truncated SVD (Latent Semantic Analysis)**:
   Embeds text into a 16-dimensional continuous semantic space to handle synonymy and paraphrased symptom descriptions.
3. **Reciprocal Rank Fusion (RRF)**:
   Combines both ranking lists without requiring score normalization:
   $$\text{RRF}(d) = \frac{1}{60 + r_{\text{BM25}}(d)} + \frac{1}{60 + r_{\text{SVD}}(d)}$$
   The top document per runbook is returned with snippet previews and executable remediation actions.
