"""Staged investigation orchestrator.

The 15 UI stages are emitted as SSE events. Each stage is a real computation or
a real tool call; the LLM (when configured) participates as a critic/narrator
inside a bounded tool-calling loop. Human approval is a hard gate implemented
with an asyncio.Event, and post-remediation the orchestrator VERIFIES recovery
against the detector — if the action was wrong, health does not recover and the
incident escalates instead of closing.
"""
from __future__ import annotations

import asyncio
import json
import time

from ..config import settings
from ..ml import features as F
from ..ml import correlate
from ..ml.rca_model import RCARanker
from . import impact as impact_mod
from . import remediation as rem
from . import tools as T
from .llm import LLMClient

STAGES = [
    ("baseline", "Baseline established"),
    ("telemetry_anomaly", "Abnormal telemetry observed"),
    ("anomaly_detected", "Anomaly confirmed"),
    ("localize_service", "Affected services identified"),
    ("collect_evidence", "Logs & events surfaced"),
    ("investigation_start", "AI investigation started"),
    ("hypotheses_generated", "Candidate causes generated"),
    ("evidence_correlated", "Evidence correlated"),
    ("root_cause_ranked", "Root cause ranked"),
    ("impact_estimated", "Business impact estimated"),
    ("remediation_proposed", "Remediation recommended"),
    ("approval_requested", "Awaiting human approval"),
    ("remediation_executing", "Remediation executing"),
    ("recovery_verified", "Recovery verified"),
    ("incident_closed", "Incident closed"),
]

SYSTEM_PROMPT = """You are the reasoning layer of NEXUS, an autonomous incident \
response system. A statistical detector and a trained classifier have already \
produced a ranked root-cause hypothesis set from real telemetry.

Your responsibilities:
1. Critique the ranking using the evidence provided. You may express \
disagreement and explain why, but you must not invent data.
2. Write a crisp operator-facing narrative: what broke, why we believe that, \
what the evidence is, and what to do.
3. Cite runbook doc_ids for every claim that comes from documentation.

Never state a number that is not present in the evidence. If evidence is \
insufficient, say so explicitly. Respond with JSON only:
{"summary": str, "reasoning": [str], "agreement": "agree"|"partial"|"disagree",
 "critique": str, "recommended_action_id": str, "citations": [str],
 "confidence": float}"""


class Investigation:
    def __init__(self, world, incident_id: str):
        self.world = world
        self.id = incident_id
        self.llm = LLMClient()
        self.ranker: RCARanker = world.ranker
        self.approval = asyncio.Event()
        self.approval_payload: dict | None = None
        self.trace: list[dict] = []
        self.tool_calls: list[dict] = []
        self.t0 = time.perf_counter()

    # ------------------------------------------------------------- plumbing
    async def emit(self, stage: str, status: str, **payload) -> None:
        ev = {"incident_id": self.id, "stage": stage, "status": status,
              "label": dict(STAGES).get(stage, stage),
              "elapsed_ms": round((time.perf_counter() - self.t0) * 1000, 1),
              "ts": time.time(), **payload}
        self.trace.append(ev)
        self.world.record_stage(self.id, ev)
        await self.world.publish_incident(self.id, "stage", ev)
        await asyncio.sleep(0.28)          # paced for a readable demo

    def _tool(self, ctx, name, **args) -> dict:
        res = T.call(ctx, name, args)
        self.tool_calls.append(res)
        return res

    # ------------------------------------------------------------------ run
    async def run(self, detection: dict) -> dict:
        w = self.world
        await self.emit("baseline", "done",
                        detail=f"Harmonic+AR(1) baselines fitted on "
                               f"{settings.warmup_ticks} clean ticks "
                               f"({settings.warmup_ticks*settings.tick_seconds/3600:.1f}h).",
                        provenance="REAL")
        await self.emit("telemetry_anomaly", "done",
                        detail=f"Fused anomaly score {detection['system_score']:.4f} "
                               f"crossed threshold {detection['threshold']:.4f}.",
                        anomaly=detection, provenance="REAL")

        window = w.window(ticks=140)
        anomaly = detection
        await self.emit("anomaly_detected", "done",
                        detail=f"{len(anomaly['firing'])} of "
                               f"{len(anomaly['services'])} services firing "
                               f"({settings.persist_k}-of-{settings.persist_n} persistence gate).",
                        provenance="REAL")

        blame = correlate.localize(window, anomaly, w.deploys_json(), settings.tick_seconds)
        await self.emit("localize_service", "done", blame=blame,
                        detail=f"Blame leader: {blame['leader']} "
                               f"(score {blame['ranking'][0]['blame']:.3f}), "
                               f"onset spread {blame['onset_spread_s']:.0f}s.",
                        provenance="REAL")

        logs = w.logs_json(since_tick=window["t_start"])
        deploys = w.deploys_json()
        impact = impact_mod.estimate(window, blame, settings.tick_seconds)
        ctx = {"window": window, "anomaly": anomaly, "blame": blame, "logs": logs,
               "deploys": deploys, "impact": impact, "now_tick": w.engine.t}

        ev_calls = [
            self._tool(ctx, "search_logs", service=blame["leader"], level="ERROR", limit=8),
            self._tool(ctx, "search_logs", query="timeout", limit=6),
            self._tool(ctx, "get_deployments", ticks=90),
            self._tool(ctx, "get_topology", service=blame["leader"]),
            self._tool(ctx, "query_metrics", service=blame["leader"], ticks=40),
        ]
        await self.emit("collect_evidence", "done", tool_calls=ev_calls,
                        detail=f"{len(logs)} log lines, {len(deploys)} change events, "
                               f"{len(ev_calls)} tool calls.",
                        provenance="REAL")

        await self.emit("investigation_start", "running",
                        detail=f"Reasoning layer: {self.llm.info()['provider']} "
                               f"({self.llm.info()['mode']}); ranker: {self.ranker.mode}.",
                        llm=self.llm.info(), provenance="REAL")

        x, fdict = F.extract(window, anomaly, blame, logs, deploys, settings.tick_seconds)
        primary, rule = self.ranker.predict(x, fdict)
        await self.emit("hypotheses_generated", "done",
                        hypotheses=primary.ranking, ranker=primary.ranker,
                        cross_check={"ranker": rule.ranker, "top": rule.top_class,
                                     "confidence": rule.confidence},
                        features=fdict,
                        detail=f"{len(primary.ranking)} candidate causes scored over "
                               f"{F.N_FEATURES} incident features.",
                        provenance="REAL")

        retrieved = rem.retrieve_for_class(primary.top_class,
                                           [blame["leader"], *blame["affected"]])
        rb_call = self._tool(ctx, "search_runbooks",
                             query=rem.CLASS_QUERY.get(primary.top_class, primary.top_class),
                             k=4, services=[blame["leader"]])
        pivot = blame["onset_tick"]
        cmp_call = self._tool(ctx, "compare_windows", service=blame["leader"],
                              metric="latency_p95", pivot_tick=pivot)
        await self.emit("evidence_correlated", "done",
                        citations=[{"doc_id": r["doc_id"], "title": r["title"],
                                    "heading": r["heading"], "score": r["score"],
                                    "snippet": r["snippet"]} for r in retrieved],
                        tool_calls=[rb_call, cmp_call],
                        detail=f"Retrieved {len(retrieved)} runbooks; onset shape at "
                               f"t={pivot}: {cmp_call['result'].get('shape')} "
                               f"(Welch t={cmp_call['result'].get('welch_t')}).",
                        provenance="REAL")

        narrative = await self._narrate(primary, rule, blame, impact, retrieved,
                                        fdict, cmp_call["result"])
        await self.emit("root_cause_ranked", "done",
                        root_cause={"class": primary.top_class,
                                    "service": blame["leader"],
                                    "confidence": primary.confidence,
                                    "margin": primary.margin,
                                    "ranker": primary.ranker},
                        narrative=narrative, evidence=primary.ranking[0]["evidence"],
                        detail=f"{primary.top_class} @ {blame['leader']} "
                               f"(p={primary.confidence:.2f}, margin={primary.margin:.2f}).",
                        provenance="REAL")

        await self.emit("impact_estimated", "done", impact=impact,
                        detail=f"{impact['severity']} · "
                               f"${impact['revenue_at_risk_usd']:.2f} at risk · "
                               f"~{impact['affected_users_est']} users · "
                               f"{len(impact['breaching_slos'])} SLOs breaching.",
                        provenance="REAL computation over SIMULATED telemetry")

        plan = rem.plan(primary.top_class, blame["leader"], impact, retrieved)
        if narrative.get("recommended_action_id"):
            for c in [plan["recommended"], *plan["alternatives"]]:
                if c["action_id"] == narrative["recommended_action_id"] and \
                        c is not plan["recommended"]:
                    plan["alternatives"].append(plan["recommended"])
                    plan["recommended"] = c
                    plan["llm_override"] = True
                    break
        await self.emit("remediation_proposed", "done", plan=plan,
                        detail=f"{plan['recommended']['label']} "
                               f"({plan['recommended']['policy_reason']}) — "
                               f"source {plan['recommended']['source_doc']}.",
                        provenance="REAL plan · SIMULATED execution")

        if plan["recommended"]["approval_required"]:
            await self.emit("approval_requested", "waiting", plan=plan,
                            detail="Human-in-the-loop gate: approval required by policy.",
                            provenance="REAL")
            try:
                await asyncio.wait_for(self.approval.wait(), timeout=300)
            except asyncio.TimeoutError:
                await self.emit("approval_requested", "timeout",
                                detail="No operator response in 5 min — auto-escalated.",
                                provenance="REAL")
                return self._finish("escalated", primary, blame, impact, plan, narrative)
            decision = self.approval_payload or {}
            if not decision.get("approve"):
                await self.emit("approval_requested", "rejected",
                                detail="Operator rejected the recommendation.",
                                provenance="REAL")
                return self._finish("rejected_by_operator", primary, blame,
                                    impact, plan, narrative)
            chosen = decision.get("action_id") or plan["recommended"]["action_id"]
            await self.emit("approval_requested", "approved",
                            detail=f"Approved: {chosen} by "
                                   f"{decision.get('operator', 'operator')}.",
                            provenance="REAL")
        else:
            chosen = plan["recommended"]["action_id"]
            await self.emit("approval_requested", "auto_approved",
                            detail="Low-risk reversible action: auto-execution permitted.",
                            provenance="REAL")

        target = plan["recommended"]["target"]
        for c in plan["alternatives"]:
            if c["action_id"] == chosen:
                target = c["target"]
        applied = w.engine.apply_action(chosen, target)
        await self.emit("remediation_executing", "done", applied=applied,
                        detail=f"Applied `{chosen}` to {target}: "
                               f"{', '.join(applied['effects'])}",
                        provenance="SIMULATED execution against the environment model")

        verdict = await self._verify()
        if verdict["recovered"]:
            await self.emit("recovery_verified", "done", verification=verdict,
                            detail=f"Health {verdict['health_before']:.1f} → "
                                   f"{verdict['health_after']:.1f}; "
                                   f"anomaly score {verdict['score_after']:.4f} "
                                   f"below threshold for {verdict['clear_ticks']} ticks.",
                            provenance="REAL verification of SIMULATED recovery")
            await self.emit("incident_closed", "done",
                            detail=f"MTTR {verdict['mttr_s']:.0f}s simulated "
                                   f"({(time.perf_counter()-self.t0):.1f}s wall).",
                            provenance="REAL")
            return self._finish("resolved", primary, blame, impact, plan,
                                narrative, verdict)
        await self.emit("recovery_verified", "failed", verification=verdict,
                        detail="System did NOT recover — the action did not address "
                               "the active fault. Escalating to human on-call.",
                        provenance="REAL")
        await self.emit("incident_closed", "escalated",
                        detail="Incident escalated; hypothesis invalidated by "
                               "the recovery check.",
                        provenance="REAL")
        return self._finish("escalated_no_recovery", primary, blame, impact, plan,
                            narrative, verdict)

    # ------------------------------------------------------------ narration
    async def _narrate(self, primary, rule, blame, impact, retrieved,
                       fdict, cmp_result) -> dict:
        evidence = {
            "detector": {"threshold": self.world.last_anomaly["threshold"],
                         "system_score": self.world.last_anomaly["system_score"]},
            "blame_ranking": blame["ranking"][:4],
            "onset_shape": cmp_result,
            "ranked_hypotheses": [{"class": h["class"], "p": h["probability"]}
                                  for h in primary.ranking[:4]],
            "top_evidence_features": primary.ranking[0]["evidence"],
            "cross_check_ranker": {"top": rule.top_class, "p": rule.confidence},
            "impact": {k: impact[k] for k in
                       ("severity", "revenue_at_risk_usd", "affected_users_est",
                        "breaching_slos", "duration_min")},
            "runbooks": [{"doc_id": r["doc_id"], "title": r["title"],
                          "heading": r["heading"], "snippet": r["snippet"],
                          "actions": r["actions"]} for r in retrieved],
        }
        res = await self.llm.complete(SYSTEM_PROMPT,
                                      "EVIDENCE\n" + json.dumps(evidence, default=str))
        parsed = LLMClient.parse_json(res.text) if not res.degraded else None
        if parsed and isinstance(parsed.get("reasoning"), list):
            parsed["source"] = f"{res.provider}:{res.model}"
            parsed["tokens"] = res.tokens
            return parsed
        return self._deterministic_narrative(primary, rule, blame, impact,
                                             retrieved, cmp_result,
                                             degraded_reason=res.error)

    def _deterministic_narrative(self, primary, rule, blame, impact, retrieved,
                                 cmp_result, degraded_reason=None) -> dict:
        leader, ranking = blame["leader"], blame["ranking"]
        top_ev = primary.ranking[0]["evidence"]
        cites = [r["doc_id"] for r in retrieved[:2]]
        agree = "agree" if rule.top_class == primary.top_class else "partial"
        reasoning = [
            f"Detector fired on {len(blame['affected'])} service(s); "
            f"{leader} carries the highest blame score "
            f"({ranking[0]['blame']:.3f}) driven by anomaly magnitude "
            f"{ranking[0]['anomaly_score']:.3f}, onset lead "
            f"{ranking[0]['onset_lead_s']:.0f}s and upstreamness "
            f"{ranking[0]['upstreamness']:.2f}.",
            f"Dominant anomalous metrics on {leader}: " + ", ".join(
                f"{m['metric']} (|z|={m['abs_z']})" for m in ranking[0]["top_metrics"]) + ".",
            f"Onset at t={blame['onset_tick']} has a "
            f"{cmp_result.get('shape', 'n/a')} profile "
            f"(Welch t={cmp_result.get('welch_t')}, "
            f"shift {cmp_result.get('shift_pct')}% on p95), which is "
            + ("consistent with a discrete change event."
               if cmp_result.get("shape") == "step"
               else "consistent with a progressive resource or load process."),
            f"The {primary.ranker} ranker assigns p={primary.confidence:.2f} to "
            f"`{primary.top_class}` with margin {primary.margin:.2f} over the "
            f"runner-up; strongest contributing features: " + ", ".join(
                f"{e['feature']}={e['value']} ({e['direction']})" for e in top_ev[:3]) + ".",
            f"Independent evidence-rule cross-check returns `{rule.top_class}` "
            f"(p={rule.confidence:.2f}) — {agree}.",
            f"Retrieved guidance {cites} matches this signature; the recommended "
            f"action is taken from that document's action manifest rather than "
            f"generated freely.",
            f"Impact: {impact['severity']}, {len(impact['breaching_slos'])} SLO(s) "
            f"breaching, ~${impact['revenue_at_risk_usd']:.2f} at risk over "
            f"{impact['duration_min']:.1f} min.",
        ]
        summary = (f"{primary.top_class.replace('_', ' ')} originating at "
                   f"{leader}. {len(blame['affected'])} services show correlated "
                   f"degradation; {leader} moved first and is upstream of "
                   f"{ranking[0]['upstreamness']:.0%} of the other affected "
                   f"services, so the remainder are propagation rather than "
                   f"independent faults.")
        return {"summary": summary, "reasoning": reasoning, "agreement": agree,
                "critique": "Deterministic analyst: no free-form generation. "
                            "Every figure above is read from computed evidence.",
                "recommended_action_id": None, "citations": cites,
                "confidence": primary.confidence,
                "source": "deterministic-analyst",
                "degraded_reason": degraded_reason}

    # ----------------------------------------------------------- verification
    async def _verify(self, need_clear: int = 6, max_ticks: int = 42) -> dict:
        w = self.world
        before = w.health["score"]
        clear = 0
        for _ in range(max_ticks):
            await asyncio.sleep(settings.wall_seconds)
            s = w.last_anomaly["system_score"]
            clear = clear + 1 if s < w.last_anomaly["threshold"] else 0
            if clear >= need_clear:
                break
        return {"recovered": clear >= need_clear, "clear_ticks": clear,
                "health_before": before, "health_after": w.health["score"],
                "score_after": w.last_anomaly["system_score"],
                "threshold": w.last_anomaly["threshold"],
                "mttr_s": round((w.engine.t - w.incident_start_tick) *
                                settings.tick_seconds, 1)}

    def _finish(self, status, primary, blame, impact, plan, narrative,
                verdict=None) -> dict:
        return {
            "incident_id": self.id, "status": status,
            "root_cause": {"class": primary.top_class, "service": blame["leader"],
                           "confidence": primary.confidence, "ranker": primary.ranker},
            "hypotheses": primary.ranking, "blame": blame, "impact": impact,
            "plan": plan, "narrative": narrative, "verification": verdict,
            "tool_calls": self.tool_calls, "trace": self.trace,
            "wall_ms": round((time.perf_counter() - self.t0) * 1000, 1),
        }
