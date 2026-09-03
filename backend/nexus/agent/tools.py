"""Tool registry. Every tool reads the real world state — no tool returns
fabricated data, and the exact arguments/results are streamed to the UI so the
investigation trace is auditable."""
from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from ..rag.store import KB
from ..simulation.topology import EDGES, SERVICES, dependents_transitive

TOOLS: dict[str, dict] = {}


def tool(name: str, description: str, params: dict):
    def deco(fn: Callable):
        TOOLS[name] = {"name": name, "description": description,
                       "parameters": params, "fn": fn}
        return fn
    return deco


@tool("query_metrics", "Aggregate telemetry for a service over the last N ticks.",
      {"service": "str", "ticks": "int", "metrics": "list[str]|None"})
def query_metrics(ctx, service: str, ticks: int = 40, metrics=None) -> dict:
    raw = ctx["window"]["raw"][service]
    metrics = metrics or list(raw.keys())
    n = min(ticks, ctx["window"]["n"])
    out = {}
    for m in metrics:
        a = np.asarray(raw[m][-n:], dtype=float)
        base = np.asarray(raw[m][: max(4, ctx["window"]["n"] - n)], dtype=float)
        out[m] = {"mean": round(float(a.mean()), 3), "p95": round(float(np.quantile(a, .95)), 3),
                  "max": round(float(a.max()), 3),
                  "baseline_mean": round(float(base.mean()), 3) if len(base) else None,
                  "delta_pct": (round(100 * (a.mean() - base.mean()) / (abs(base.mean()) + 1e-9), 1)
                                if len(base) else None)}
    return {"service": service, "ticks": n, "aggregates": out,
            "anomaly": ctx["anomaly"]["services"][service]}


@tool("search_logs", "Search recent log lines by substring/level/service.",
      {"query": "str", "service": "str|None", "level": "str|None", "limit": "int"})
def search_logs(ctx, query: str = "", service=None, level=None, limit: int = 12) -> dict:
    q = query.lower()
    hits = [l for l in ctx["logs"]
            if (not service or l["service"] == service)
            and (not level or l["level"] == level)
            and (not q or q in l["message"].lower() or q in l["pattern"])]
    counts: dict[str, int] = {}
    for l in hits:
        counts[l["pattern"]] = counts.get(l["pattern"], 0) + 1
    return {"total": len(hits), "pattern_counts": counts, "lines": hits[-limit:]}


@tool("get_deployments", "List deployment/config-change events in the window.",
      {"ticks": "int"})
def get_deployments(ctx, ticks: int = 80) -> dict:
    cut = ctx["now_tick"] - ticks
    ds = [d for d in ctx["deploys"] if d["tick"] >= cut]
    return {"count": len(ds), "deployments": ds,
            "note": "Correlation only — deploy proximity is one feature, not proof."}


@tool("get_topology", "Dependency graph, callers and transitive blast radius.",
      {"service": "str|None"})
def get_topology(ctx, service=None) -> dict:
    if service:
        return {"service": service, "kind": SERVICES[service].kind,
                "depends_on": SERVICES[service].deps,
                "called_by": [s for s, sp in SERVICES.items() if service in sp.deps],
                "blast_radius": sorted(dependents_transitive(service))}
    return {"nodes": [{"id": s, "kind": sp.kind, "tier": sp.tier} for s, sp in SERVICES.items()],
            "edges": [{"from": a, "to": b, "fanout": f} for a, b, f in EDGES]}


@tool("search_runbooks", "Hybrid retrieval over the engineering knowledge base.",
      {"query": "str", "k": "int", "services": "list[str]|None"})
def search_runbooks(ctx, query: str, k: int = 4, services=None) -> dict:
    res = KB.search(query, k=k, services=services)
    return {"query": query, "results": res, "retriever": KB.stats()["retriever"]}


@tool("read_runbook", "Read a full runbook document by id.", {"doc_id": "str"})
def read_runbook(ctx, doc_id: str) -> dict:
    d = KB.doc(doc_id)
    return d or {"error": f"unknown doc_id {doc_id}"}


@tool("get_blame_ranking", "Dependency-aware fault localization ranking.", {})
def get_blame_ranking(ctx) -> dict:
    return ctx["blame"]


@tool("estimate_impact", "SLO-error-budget and revenue-at-risk impact estimate.", {})
def estimate_impact(ctx) -> dict:
    return ctx["impact"]


@tool("compare_windows", "Pre/post statistical comparison around a tick.",
      {"service": "str", "metric": "str", "pivot_tick": "int"})
def compare_windows(ctx, service: str, metric: str, pivot_tick: int) -> dict:
    w = ctx["window"]
    i = max(2, min(w["n"] - 2, pivot_tick - w["t_start"]))
    a = np.asarray(w["raw"][service][metric][:i], dtype=float)
    b = np.asarray(w["raw"][service][metric][i:], dtype=float)
    sd = np.sqrt((a.var(ddof=1) / len(a)) + (b.var(ddof=1) / len(b))) + 1e-9
    return {"service": service, "metric": metric, "pivot_tick": pivot_tick,
            "pre_mean": round(float(a.mean()), 3), "post_mean": round(float(b.mean()), 3),
            "welch_t": round(float((b.mean() - a.mean()) / sd), 2),
            "shift_pct": round(100 * (b.mean() - a.mean()) / (abs(a.mean()) + 1e-9), 1),
            "shape": "step" if abs(float((b.mean() - a.mean()) / sd)) > 8 else "ramp"}


def call(ctx: dict, name: str, args: dict) -> dict:
    t0 = time.perf_counter()
    spec = TOOLS.get(name)
    if not spec:
        return {"tool": name, "ok": False, "error": "unknown_tool", "ms": 0.0}
    try:
        result: Any = spec["fn"](ctx, **args)
        ok, err = True, None
    except Exception as e:                            # noqa: BLE001
        result, ok, err = {}, False, f"{type(e).__name__}: {e}"
    return {"tool": name, "args": args, "ok": ok, "error": err, "result": result,
            "ms": round((time.perf_counter() - t0) * 1000, 2)}


def openai_schema() -> list[dict]:
    return [{"type": "function", "function": {
        "name": t["name"], "description": t["description"],
        "parameters": {"type": "object",
                       "properties": {k: {"type": "string"} for k in t["parameters"]}}}}
        for t in TOOLS.values()]
