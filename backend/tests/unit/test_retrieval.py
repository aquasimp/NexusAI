"""Unit tests for runbook knowledge base search and retrieval."""
from nexus.rag.store import KB

def test_kb_contains_documents():
    """Verify all 10 standard SRE runbooks are indexed in KB."""
    stats = KB.stats()
    assert stats["documents"] == 10
    assert stats["chunks"] >= 10
    assert stats["vocabulary"] > 50

def test_kb_bm25_and_svd_search():
    """Verify hybrid search returns relevant runbooks for known incident queries."""
    results = KB.search("postgres connection pool exhaustion max connections timeout", k=3)
    assert len(results) > 0
    top_ids = [r["doc_id"] for r in results]
    assert "rb-postgres-pool" in top_ids or "rb-postgres-latency" in top_ids

    redis_results = KB.search("redis evictions memory leak maxmemory cache miss", k=3)
    assert len(redis_results) > 0
    redis_top = [r["doc_id"] for r in redis_results]
    assert "rb-redis-eviction" in redis_top or "rb-memory-leak" in redis_top
