"""Hybrid lexical retrieval over the runbook corpus.

BM25 (exact term / error-code matching) fused with TF-IDF + Truncated SVD
(latent semantic, handles paraphrase) via Reciprocal Rank Fusion. Chosen over a
neural embedding model deliberately: zero-download, deterministic, CPU-only, and
on a 60-chunk technical corpus with high term overlap it is competitive — the
Evaluation page reports the measured retrieval quality so the trade-off is
auditable rather than asserted. Swapping in bge-small + pgvector is a one-class
change (see README > Future production architecture).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

CORPUS_DIR = Path(__file__).parent / "corpus"
TOKEN = re.compile(r"[a-z0-9_\-/\.]+")


def tokenize(s: str) -> list[str]:
    return TOKEN.findall(s.lower())


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    heading: str
    text: str
    tags: list[str]
    services: list[str]
    actions: list[dict]


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, fm, body = raw.split("---", 2)
    meta: dict = {}
    key = None
    for line in fm.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and key:
            item = line[4:].strip()
            if ":" in item and key == "actions":
                d = {}
                for part in item.split("; "):
                    k, _, v = part.partition(":")
                    d[k.strip()] = v.strip()
                meta[key].append(d)
            else:
                meta[key].append(item)
        elif ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            meta[key] = val if val else []
    return meta, body


class KnowledgeBase:
    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.chunks: list[Chunk] = []
        self.docs: dict[str, dict] = {}
        self._load(corpus_dir)
        self._index()

    def _load(self, d: Path) -> None:
        for path in sorted(d.glob("*.md")):
            meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
            doc_id = meta.get("id", path.stem)
            self.docs[doc_id] = {
                "id": doc_id, "title": meta.get("title", path.stem),
                "tags": meta.get("tags", []) or [],
                "services": meta.get("services", []) or [],
                "actions": meta.get("actions", []) or [],
                "path": path.name, "body": body.strip(),
            }
            heading, buf = "Overview", []

            def flush(h, b):
                text = "\n".join(b).strip()
                if len(text) > 40:
                    self.chunks.append(Chunk(
                        f"{doc_id}#{len(self.chunks)}", doc_id,
                        self.docs[doc_id]["title"], h, text,
                        self.docs[doc_id]["tags"], self.docs[doc_id]["services"],
                        self.docs[doc_id]["actions"]))

            for line in body.splitlines():
                if line.startswith("## "):
                    flush(heading, buf)
                    heading, buf = line[3:].strip(), []
                else:
                    buf.append(line)
            flush(heading, buf)

    def _index(self) -> None:
        corpus = [f"{c.title} {c.heading} {' '.join(c.tags)} "
                  f"{' '.join(c.services)} {c.text}" for c in self.chunks]
        self.tfidf = TfidfVectorizer(tokenizer=tokenize, lowercase=True,
                                     sublinear_tf=True, min_df=1, token_pattern=None)
        self.X = self.tfidf.fit_transform(corpus)
        k = max(2, min(48, self.X.shape[0] - 1, self.X.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=3)
        self.L = self.svd.fit_transform(self.X)
        self.Ln = self.L / (np.linalg.norm(self.L, axis=1, keepdims=True) + 1e-9)

        self.toks = [tokenize(c) for c in corpus]
        self.dl = np.array([len(t) for t in self.toks], dtype=float)
        self.avgdl = float(self.dl.mean())
        self.df: dict[str, int] = {}
        for t in self.toks:
            for w in set(t):
                self.df[w] = self.df.get(w, 0) + 1
        self.N = len(self.toks)
        self.tf = [{w: t.count(w) for w in set(t)} for t in self.toks]

    # ------------------------------------------------------------- scoring
    def _bm25(self, q: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        s = np.zeros(self.N)
        for w in q:
            n = self.df.get(w)
            if not n:
                continue
            idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for i in range(self.N):
                f = self.tf[i].get(w, 0)
                if f:
                    s[i] += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * self.dl[i] / self.avgdl))
        return s

    def search(self, query: str, k: int = 5, services: list[str] | None = None) -> list[dict]:
        q = tokenize(query)
        if not q:
            return []
        bm = self._bm25(q)
        qv = self.tfidf.transform([query])
        lat = (self.svd.transform(qv) /
               (np.linalg.norm(self.svd.transform(qv)) + 1e-9)) @ self.Ln.T
        lat = lat.ravel()

        rrf = np.zeros(self.N)
        for scores, w in ((bm, 1.0), (lat, 0.85)):
            ranks = np.empty(self.N, dtype=int)
            ranks[np.argsort(-scores)] = np.arange(self.N)
            rrf += w / (60.0 + ranks + 1)
        if services:
            boost = np.array([1.18 if set(c.services) & set(services) else 1.0
                              for c in self.chunks])
            rrf *= boost

        out = []
        for i in np.argsort(-rrf)[: k * 3]:
            c = self.chunks[i]
            out.append({
                "chunk_id": c.id, "doc_id": c.doc_id, "title": c.title,
                "heading": c.heading, "tags": c.tags, "services": c.services,
                "actions": c.actions, "score": round(float(rrf[i]), 6),
                "bm25": round(float(bm[i]), 3), "lsa": round(float(lat[i]), 4),
                "snippet": c.text[:340].replace("\n", " ").strip() + "…",
            })
        seen, dedup = set(), []
        for r in out:                       # one best chunk per document
            if r["doc_id"] in seen:
                continue
            seen.add(r["doc_id"])
            dedup.append(r)
            if len(dedup) == k:
                break
        return dedup

    def doc(self, doc_id: str) -> dict | None:
        return self.docs.get(doc_id)

    def stats(self) -> dict:
        return {"documents": len(self.docs), "chunks": len(self.chunks),
                "vocabulary": len(self.df), "svd_components": int(self.svd.n_components),
                "retriever": "BM25 + TF-IDF/SVD (RRF fusion)"}


KB = KnowledgeBase()
