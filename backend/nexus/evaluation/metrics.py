"""Metric primitives. No metric is hard-coded anywhere in this project — every
number rendered on the Evaluation page is produced by these functions at run
time from benchmark episodes."""
from __future__ import annotations
import numpy as np


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
            "tp": tp, "fp": fp, "fn": fn}


def pr_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Average precision via the step-wise PR curve (no sklearn dependency here
    so the number is trivially auditable)."""
    order = np.argsort(-scores)
    y = labels[order]
    tp = np.cumsum(y)
    prec = tp / np.arange(1, len(y) + 1)
    npos = y.sum()
    return round(float((prec * y).sum() / npos) if npos else 0.0, 4)


def topk_accuracy(ranked: list[list[str]], truth: list[str], k: int) -> float:
    if not truth:
        return 0.0
    hits = sum(1 for r, t in zip(ranked, truth) if t in r[:k])
    return round(hits / len(truth), 4)


def macro_f1(y_true: list[str], y_pred: list[str], classes: list[str]) -> dict:
    per = {}
    fs = []
    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        per[c] = prf(tp, fp, fn)
        if tp + fn:
            fs.append(per[c]["f1"])
    return {"per_class": per, "macro_f1": round(float(np.mean(fs)) if fs else 0.0, 4)}


def confusion(y_true: list[str], y_pred: list[str], classes: list[str]) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(classes)}
    M = [[0] * len(classes) for _ in classes]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            M[idx[t]][idx[p]] += 1
    return M


def retrieval(retrieved: list[list[str]], gold: list[list[str]], k: int) -> dict:
    recalls, mrrs, ndcgs, precs = [], [], [], []
    for r, g in zip(retrieved, gold):
        rk, gs = r[:k], set(g)
        if not gs:
            continue
        recalls.append(len(set(rk) & gs) / len(gs))
        precs.append(len(set(rk) & gs) / max(1, len(rk)))
        rr = next((1 / (i + 1) for i, d in enumerate(rk) if d in gs), 0.0)
        mrrs.append(rr)
        dcg = sum((1 / np.log2(i + 2)) for i, d in enumerate(rk) if d in gs)
        idcg = sum(1 / np.log2(i + 2) for i in range(min(len(gs), k)))
        ndcgs.append(dcg / idcg if idcg else 0.0)
    m = lambda a: round(float(np.mean(a)) if a else 0.0, 4)  # noqa: E731
    return {f"recall@{k}": m(recalls), f"precision@{k}": m(precs),
            "mrr": m(mrrs), f"ndcg@{k}": m(ndcgs), "n": len(recalls)}


def latency_stats(ms: list[float]) -> dict:
    if not ms:
        return {"n": 0}
    a = np.asarray(ms, dtype=float)
    return {"n": len(a), "mean_ms": round(float(a.mean()), 2),
            "p50_ms": round(float(np.quantile(a, .5)), 2),
            "p95_ms": round(float(np.quantile(a, .95)), 2),
            "max_ms": round(float(a.max()), 2)}


def wilson_ci(k: int, n: int, z: float = 1.96) -> list[float]:
    """95% CI on an accuracy. Reported everywhere because n is small (~84) and
    a bare point estimate at that sample size is not honest."""
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]
