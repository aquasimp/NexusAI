"""The live world: one shared simulation + detector + investigation lifecycle."""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque

import numpy as np

from . import store
from .agent.orchestrator import Investigation
from .config import settings
from .hub import hub
from .ml.detector import Detector
from .ml.rca_model import RCARanker
from .sim.engine import Engine
from .sim.logs import synthesize, to_dict
from .sim.scenarios import SCENARIOS, arm
from .sim.topology import METRICS, SERVICES


class World:
    def __init__(self):
        self.engine = Engine(seed=int(time.time()) % 9973,
                             tick_seconds=settings.tick_seconds)
        self.detector = Detector(settings.harmonics, settings.detect_quantile,
                                 settings.persist_k, settings.persist_n)
        self.ranker = RCARanker()
        self.frames: deque = deque(maxlen=settings.buffer_ticks)
        self.times: deque = deque(maxlen=settings.buffer_ticks)
        self.ticks: deque = deque(maxlen=settings.buffer_ticks)
        self.zbuf: deque = deque(maxlen=settings.buffer_ticks)
        self.logs: deque = deque(maxlen=4000)
        self.last_anomaly: dict = {}
        self.health: dict = {"score": 100.0, "status": "healthy", "services": {}}
        self.armed_scenario: str | None = None
        self.active_incident: str | None = None
        self.incident_start_tick: int = 0
        self.investigations: dict[str, Investigation] = {}
        self.stages: dict[str, list] = {}
        self.state: str = "booting"
        self._task: asyncio.Task | None = None
        self._rng = np.random.default_rng(5)

    # ------------------------------------------------------------------ boot
    def warmup(self) -> dict:
        t0 = time.perf_counter()
        e = Engine(seed=101, tick_seconds=settings.tick_seconds)
        times, hist = [], {s: {m: [] for m in METRICS} for s in SERVICES}
        for _ in range(settings.warmup_ticks):
            times.append(e.sim_time())
            f = e.tick()
            for s in SERVICES:
                for m in METRICS:
                    hist[s][m].append(f[s][m])
        H = {s: {m: np.asarray(v, dtype=float) for m, v in d.items()}
             for s, d in hist.items()}
        self.detector.fit(np.asarray(times, dtype=float), H)
        self.state = "running"
        return {"warmup_ticks": settings.warmup_ticks,
                "sim_hours": round(settings.warmup_ticks * settings.tick_seconds / 3600, 2),
                "fit_seconds": round(time.perf_counter() - t0, 2),
                "threshold": self.detector.threshold}

    async def start(self) -> None:
        self.dstate = self.detector.new_state()
        for _ in range(90):                     # pre-fill the UI buffer
            self._tick_once()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    # ------------------------------------------------------------------ tick
    def _tick_once(self) -> dict:
        t = self.engine.t
        ts = self.engine.sim_time()
        deploys_now = [d for d in self.engine.deploys if d.tick == t]
        frame = self.engine.tick()
        an = self.detector.score_frame(self.dstate, ts, frame)
        for l in synthesize(t, ts, frame, self._rng, deploys_now):
            self.logs.append(to_dict(l))

        self.ticks.append(t); self.times.append(ts); self.frames.append(frame)
        self.zbuf.append({s: [an["services"][s]["z"][m] for m in METRICS]
                          for s in SERVICES})
        self.last_anomaly = an
        self.health = self._health(frame, an)
        return {"tick": t, "sim_ts": ts, "frame": frame, "anomaly": an,
                "health": self.health}

    def _health(self, frame, an) -> dict:
        per, tot, wsum = {}, 0.0, 0.0
        for sid, spec in SERVICES.items():
            m = frame[sid]
            e = min(1.0, max(0.0, (m["error_rate"] - spec.slo_error_pct)
                             / max(0.5, 8 * spec.slo_error_pct)))
            l = min(1.0, max(0.0, (m["latency_p95"] - spec.slo_p95_ms)
                             / max(1.0, 3 * spec.slo_p95_ms)))
            pen = 1.0 - (0.62 * e + 0.38 * l)
            w = 3.0 if spec.kind in ("edge", "datastore") else \
                2.0 if sid == "payment-service" else 1.0
            score = round(100 * max(0.0, pen), 1)
            per[sid] = {"score": score,
                        "status": "healthy" if score > 92 else
                                  "degraded" if score > 65 else "critical",
                        "anomaly": an["services"][sid]["score"],
                        "firing": an["services"][sid]["firing"],
                        **{k: m[k] for k in ("rps", "latency_p50", "latency_p95",
                                             "error_rate", "cpu", "mem", "utilization")}}
            tot += score * w; wsum += w
        s = round(tot / wsum, 1)
        return {"score": s,
                "status": "healthy" if s > 92 else "degraded" if s > 70 else "critical",
                "services": per,
                "active_incident": self.active_incident,
                "armed_scenario": self.armed_scenario}

    async def _loop(self) -> None:
        while True:
            try:
                snap = self._tick_once()
                await hub.publish("live", "tick", {
                    "tick": snap["tick"], "sim_ts": snap["sim_ts"],
                    "health": snap["health"],
                    "anomaly": {"threshold": snap["anomaly"]["threshold"],
                                "system_score": snap["anomaly"]["system_score"],
                                "firing": snap["anomaly"]["firing"],
                                "anomalous_fraction": snap["anomaly"]["anomalous_fraction"],
                                "services": {k: {"score": v["score"],
                                                 "firing": v["firing"],
                                                 "top_metrics": v["top_metrics"]}
                                             for k, v in snap["anomaly"]["services"].items()}},
                    "logs": list(self.logs)[-6:],
                })
                if snap["anomaly"]["firing"] and not self.active_incident:
                    await self._open_incident(snap["anomaly"])
            except asyncio.CancelledError:
                raise
            except Exception as e:              # keep the demo alive
                await hub.publish("live", "error", {"message": str(e)})
            await asyncio.sleep(settings.wall_seconds)

    # -------------------------------------------------------------- incidents
    async def _open_incident(self, anomaly: dict) -> None:
        iid = f"INC-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        self.active_incident = iid
        self.incident_start_tick = self.engine.t
        self.stages[iid] = []
        inv = Investigation(self, iid)
        self.investigations[iid] = inv
        store.upsert_incident({"id": iid, "created_at": time.time(),
                               "scenario": self.armed_scenario, "status": "investigating"})
        await hub.publish("live", "incident_opened",
                          {"incident_id": iid, "detected_at_tick": self.engine.t,
                           "firing": anomaly["firing"],
                           "system_score": anomaly["system_score"]})
        asyncio.create_task(self._drive(inv, anomaly))

    async def _drive(self, inv: Investigation, anomaly: dict) -> None:
        try:
            result = await inv.run(anomaly)
        except Exception as e:                                    # noqa: BLE001
            result = {"incident_id": inv.id, "status": "failed", "error": repr(e),
                      "trace": inv.trace, "tool_calls": inv.tool_calls}
            await hub.publish(f"inc:{inv.id}", "error", {"message": repr(e)})
        result.setdefault("created_at", time.time())
        result["scenario"] = self.armed_scenario
        result["ground_truth"] = (
            {"root_service": SCENARIOS[self.armed_scenario].root_service,
             "root_class": SCENARIOS[self.armed_scenario].root_class,
             "gold_actions": list(SCENARIOS[self.armed_scenario].gold_actions),
             "disclosure": "Revealed only AFTER the investigation completes; "
                           "never available to the pipeline."}
            if self.armed_scenario else None)
        store.upsert_incident({"id": inv.id, **result})
        await hub.publish("live", "incident_closed",
                          {"incident_id": inv.id, "status": result["status"]})
        self.active_incident = None
        self.armed_scenario = None

    def record_stage(self, iid: str, ev: dict) -> None:
        self.stages.setdefault(iid, []).append(ev)

    async def publish_incident(self, iid: str, event: str, data: dict) -> None:
        await hub.publish(f"inc:{iid}", event, data)
        await hub.publish("live", "stage", {"incident_id": iid, "stage": data["stage"],
                                            "status": data["status"],
                                            "label": data["label"]})

    def simulate(self, scenario_id: str) -> dict:
        if self.active_incident:
            return {"ok": False, "reason": "incident_in_flight",
                    "incident_id": self.active_incident}
        if scenario_id == "random":
            scenario_id = str(self._rng.choice(list(SCENARIOS)))
        sc = arm(self.engine, scenario_id, rng_jitter=float(self._rng.uniform(0.85, 1.2)))
        self.armed_scenario = scenario_id
        return {"ok": True, "scenario": scenario_id, "title": sc.title,
                "armed_at_tick": self.engine.t,
                "note": "Root fault injected. Detection, localization and root-cause "
                        "inference receive no label — symptoms propagate through the "
                        "dependency graph on their own."}

    def approve(self, iid: str, approve: bool, action_id: str | None,
                operator: str) -> dict:
        inv = self.investigations.get(iid)
        if not inv:
            return {"ok": False, "reason": "unknown_incident"}
        inv.approval_payload = {"approve": approve, "action_id": action_id,
                                "operator": operator}
        inv.approval.set()
        return {"ok": True, "incident_id": iid, "approved": approve}

    def reset(self) -> dict:
        self.engine = Engine(seed=int(time.time()) % 9973,
                             tick_seconds=settings.tick_seconds)
        self.dstate = self.detector.new_state()
        for d in (self.frames, self.times, self.ticks, self.zbuf, self.logs):
            d.clear()
        self.active_incident = None
        self.armed_scenario = None
        for _ in range(90):
            self._tick_once()
        return {"ok": True, "tick": self.engine.t}

    # ----------------------------------------------------------------- views
    def window(self, ticks: int = 140) -> dict:
        n = min(ticks, len(self.frames))
        fr = list(self.frames)[-n:]
        zb = list(self.zbuf)[-n:]
        raw = {s: {m: np.asarray([f[s][m] for f in fr], dtype=float) for m in METRICS}
               for s in SERVICES}
        z = {s: np.asarray([row[s] for row in zb], dtype=float) for s in SERVICES}
        return {"n": n, "t_start": list(self.ticks)[-n], "t_end": list(self.ticks)[-1],
                "times": list(self.times)[-n:], "raw": raw, "z": z}

    def series_json(self, ticks: int = 180) -> dict:
        n = min(ticks, len(self.frames))
        fr = list(self.frames)[-n:]
        return {"ticks": list(self.ticks)[-n:], "times": list(self.times)[-n:],
                "tick_seconds": settings.tick_seconds,
                "series": {s: {m: [round(f[s][m], 4) for f in fr] for m in METRICS}
                           for s in SERVICES}}

    def logs_json(self, since_tick: int = 0, limit: int = 1200) -> list[dict]:
        return [l for l in self.logs if l["tick"] >= since_tick][-limit:]

    def deploys_json(self) -> list[dict]:
        return [{"tick": d.tick, "service": d.service, "version": d.version,
                 "author": d.author, "change": d.change, "risk": d.risk}
                for d in self.engine.deploys]


world = World()
