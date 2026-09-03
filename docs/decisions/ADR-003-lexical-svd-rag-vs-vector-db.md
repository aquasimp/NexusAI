# ADR-003: Lexical BM25 + SVD Latent Retrieval vs. External Vector DB

## Status
Accepted

## Context
Deploying heavyweight vector databases (Milvus, Pinecone, Qdrant, Chroma) and embedding servers introduces external daemon dependencies, GPU memory requirements, and network latency for a fixed corpus of operational SRE runbooks.

## Decision
Implement an in-memory hybrid retrieval engine utilizing:
1. Pure Python BM25 for technical keyword matching.
2. Scikit-learn TF-IDF + TruncatedSVD for latent semantic representation.
3. Reciprocal Rank Fusion (RRF) for rank-invariant aggregation.

## Consequences
- **Positive**: Zero external services; starts up instantly in <100ms; reproducible across environments; offline testable.
- **Negative**: For corpora scaling past 100,000 documents, an external ANN index would be necessary (identified as a PRODUCTION-GAP).
