from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import store
from ..agent.llm import LLMClient
from ..agent.orchestrator import STAGES
from ..config import settings
from ..eval import benchmark
from ..hub import hub
from ..rag.store import KB
from ..sim.scenarios import SCENARIOS
from ..sim.topology import EDGES, SERVICES
from ..world import world

router = APIRouter()
_eval_lock = asyncio.Lock()


@router.get("/health")
def health():
    return {"ok": True, "state": world.state, "tick": world.engine.t,
            "system_health": world.health["score"]}


@router.get("/system/info")
def system_info():
    return {
        "state": world.state, "tick": world.engine.t,
        "tick_seconds": settings.tick_seconds, "wall_seconds": settings.wall_seconds,
        "llm": LLMClient().info(), "ranker": world.ranker.info(),
        "detector": {"fitted": world.detector.fitted,
                     "threshold": round(world.detector.threshold, 5),
                     "harmonics": settings.harmonics,
                     "warmup_ticks": settings.warmup_ticks,
                     "persistence": f"{settings.persist_k}-of-{settings.persist_n}",
                     "method": "harmonic baseline + AR(1) whitening + MAD scaling "
                               "-> Ledoit-Wolf Mahalanobis + IsolationForest (RRF-free "
                               "percentile fusion)"},
        "knowledge_base": KB.stats(), "stages": [{"id": a, "label": b} for a, b in STAGES],
        "scenarios": [{"id": s.id, "title": s.title, "blurb": s.blurb,
                       "severity": s.severity} for s in SCENARIOS.values()],
        "provenance": {
            "real": ["anomaly detection", "changepoint onset", "graph localization",
                     "feature extraction", "RCA classifier", "hybrid retrieval",
                     "impact computation", "policy engine", "agent tool loop",
                     "benchmark + all metrics"],
            "simulated": ["telemetry", "logs", "deploy events",
                          "remediation effects on the environment"],
            "production_gap": ["OTel/Prometheus ingest", "streaming transport",
                               "neural embeddings + vector DB",
                               "real Kubernetes/DB actuation", "on-call paging"],
        },
    }


@router.get("/topology")
def topology():
    return {"nodes": [{"id": s.id, "name": s.name, "kind": s.kind, "tier": s.tier,
                       "owner": s.owner, "replicas": s.replicas,
                       "slo_p95_ms": s.slo_p95_ms, "slo_error_pct": s.slo_error_pct,
                       "capacity_rps": s.replicas * s.rps_per_replica,
                       "timeout_ms": s.timeout_ms}
                      for s in SERVICES.values()],
            "edges": [{"source": a, "target": b, "fanout": f} for a, b, f in EDGES]}


@router.get("/telemetry")
def telemetry(ticks: int = 180):
    return world.series_json(ticks)


@router.get("/state")
def state():
    return {"tick": world.engine.t, "health": world.health,
            "anomaly": world.last_anomaly, "active_incident": world.active_incident,
            "armed_scenario": world.armed_scenario,
            "active_faults": [{"id": f.id, "target": f.target, "kind": f.kind,
                               "intensity": round(f.intensity(world.engine.t), 4)}
                              for f in world.engine.active_faults()],
            "faults_disclosure": "Exposed for demo transparency only — the "
                                 "detection and RCA pipeline never reads this.",
            "logs": world.logs_json(limit=60), "deploys": world.deploys_json()}


@router.get("/logs")
def logs(limit: int = 200, service: str | None = None, level: str | None = None):
    ls = world.logs_json(limit=2000)
    if service:
        ls = [l for l in ls if l["service"] == service]
    if level:
        ls = [l for l in ls if l["level"] == level]
    return {"count": len(ls), "logs": ls[-limit:]}


class SimulateBody(BaseModel):
    scenario: str = Field("random")


@router.post("/simulate")
def simulate(body: SimulateBody):
    if body.scenario != "random" and body.scenario not in SCENARIOS:
        raise HTTPException(400, f"unknown scenario {body.scenario}")
    return world.simulate(body.scenario)


@router.post("/reset")
def reset():
    return world.reset()


class ApprovalBody(BaseModel):
    approve: bool
    action_id: str | None = None
    operator: str = "demo-operator"


@router.post("/incidents/{iid}/approve")
def approve(iid: str, body: ApprovalBody):
    r = world.approve(iid, body.approve, body.action_id, body.operator)
    if not r["ok"]:
        raise HTTPException(404, r["reason"])
    return r


@router.get("/incidents")
def incidents():
    return {"active": world.active_incident, "incidents": store.list_incidents()}


@router.get("/incidents/{iid}")
def incident(iid: str):
    rec = store.get_incident(iid)
    stages = world.stages.get(iid, [])
    if not rec and not stages:
        raise HTTPException(404, "unknown incident")
    return {"incident_id": iid, "record": rec, "stages": stages,
            "in_flight": iid == world.active_incident}


@router.get("/kb/search")
def kb_search(q: str, k: int = 5):
    return {"query": q, "results": KB.search(q, k=k), "stats": KB.stats()}


@router.get("/kb/docs")
def kb_docs():
    return {"documents": [{k: v for k, v in d.items() if k != "body"}
                          for d in KB.docs.values()]}


@router.get("/kb/docs/{doc_id}")
def kb_doc(doc_id: str):
    d = KB.doc(doc_id)
    if not d:
        raise HTTPException(404, "unknown doc")
    return d


@router.get("/evaluation")
def evaluation():
    run = store.latest_eval()
    if not run:
        return {"available": False,
                "message": "No benchmark run found. Execute `make eval` (or "
                           "`python -m nexus.eval.runner --quick`). This page "
                           "renders only measured values — it will stay empty "
                           "rather than display placeholder numbers."}
    return {"available": True, "run": run}


class EvalBody(BaseModel):
    seeds: int = 4
    clean: int = 8


@router.post("/evaluation/run")
async def eval_run(body: EvalBody):
    if _eval_lock.locked():
        raise HTTPException(409, "a benchmark run is already in progress")
    async with _eval_lock:
        loop = asyncio.get_running_loop()
        run = await loop.run_in_executor(
            None, lambda: benchmark.run(max(1, min(body.seeds, 20)),
                                        max(0, min(body.clean, 40))))
        store.save_eval(run)
    return {"available": True, "run": run}


async def _sse(channel: str, request: Request, initial: dict | None = None):
    q = hub.subscribe(channel)
    try:
        if initial is not None:
            yield f"event: init\ndata: {json.dumps(initial, default=str)}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                yield await asyncio.wait_for(q.get(), timeout=12.0)
            except asyncio.TimeoutError:
                yield f": keepalive {time.time()}\n\n"
    finally:
        hub.unsubscribe(channel, q)


@router.get("/stream/live")
async def stream_live(request: Request):
    init = {"tick": world.engine.t, "health": world.health,
            "anomaly": {"threshold": world.last_anomaly.get("threshold"),
                        "system_score": world.last_anomaly.get("system_score")},
            "active_incident": world.active_incident,
            "telemetry": world.series_json(120)}
    return StreamingResponse(_sse("live", request, init),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.get("/stream/incident/{iid}")
async def stream_incident(iid: str, request: Request):
    return StreamingResponse(
        _sse(f"inc:{iid}", request, {"incident_id": iid,
                                     "stages": world.stages.get(iid, [])}),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
