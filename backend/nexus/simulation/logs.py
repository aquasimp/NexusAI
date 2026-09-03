"""Log synthesis. Log *rates* are driven by the simulated metric state, so the
log-pattern features the RCA model consumes carry genuine signal."""
from __future__ import annotations
import math
from dataclasses import asdict, dataclass

import numpy as np

from .topology import SERVICES

PATTERNS = {
    "timeout": "upstream timeout after {ms}ms calling {dep} (deadline {to}ms)",
    "lock_wait": "process holding lock for {ms}ms; waiting on relation orders_pk",
    "slow_query": "duration: {ms}ms  statement: SELECT ... FROM settlements WHERE ...",
    "pool_exhausted": "HikariCP pool exhausted: active=200 idle=0 waiting={q}",
    "oom": "GC overhead limit approaching: heap {mem}% after full GC; restarting worker",
    "schema_reject": "request rejected: schema validation failed field=amount_minor (500)",
    "http_5xx": "{code} upstream_reset code={code} route={route} rt={ms}ms",
    "cache_miss": "cache miss ratio {ratio}% over 60s window (evictions={ev}/s)",
    "circuit_open": "circuit breaker OPEN for {dep} (failures={n}/20)",
    "deploy": "rollout {ver} -> {n} replicas complete (strategy=RollingUpdate)",
    "cpu_throttle": "cgroup cpu.stat throttled_time increased by {ms}ms/period",
}

ROUTES = ["/v1/checkout", "/v1/session", "/v1/feed", "/v1/profile", "/v1/notify"]


@dataclass
class LogLine:
    tick: int
    ts: float
    service: str
    level: str
    pattern: str
    message: str


def synthesize(tick: int, ts: float, frame: dict, rng: np.random.Generator,
               deploys_this_tick: list) -> list[LogLine]:
    out: list[LogLine] = []

    def emit(sid, level, pat, **kw):
        out.append(LogLine(tick, ts, sid, level, pat, PATTERNS[pat].format(**kw)))

    for d in deploys_this_tick:
        emit(d.service, "INFO", "deploy", ver=d.version,
             n=int(SERVICES[d.service].replicas))

    for sid, m in frame.items():
        spec = SERVICES[sid]
        err, p95, u = m["error_rate"], m["latency_p95"], m.get("utilization", 0.0)

        n_err = int(rng.poisson(min(14.0, 0.10 * err + 0.05)))
        for _ in range(n_err):
            if p95 > 0.7 * spec.timeout_ms and spec.deps:
                dep = max(spec.deps, key=lambda d: frame.get(d, {}).get("latency_p95", 0))
                emit(sid, "ERROR", "timeout", ms=int(p95), dep=dep, to=int(spec.timeout_ms))
            elif sid == "api-gateway" and err > 8 and p95 < 2.2 * spec.slo_p95_ms:
                emit(sid, "ERROR", "schema_reject")
            else:
                emit(sid, "ERROR", "http_5xx", code=rng.choice([500, 502, 503]),
                     route=rng.choice(ROUTES), ms=int(p95))

        if spec.kind == "datastore" and p95 > 3 * spec.slo_p95_ms:
            for _ in range(int(rng.poisson(2.2))):
                emit(sid, "WARN", "lock_wait", ms=int(p95 * rng.uniform(1.2, 3.0)))
            emit(sid, "WARN", "slow_query", ms=int(p95 * rng.uniform(1.0, 2.4)))
        if spec.kind == "cache" and p95 > 4 * spec.slo_p95_ms:
            emit(sid, "WARN", "cache_miss",
                 ratio=round(min(96.0, 18 + p95 * 2.5), 1), ev=int(p95 * 40))
        if m.get("mem", 0) > 88:
            emit(sid, "WARN", "oom", mem=round(m["mem"], 1))
        if m.get("oom_restart"):
            emit(sid, "FATAL", "oom", mem=round(m["mem"], 1))
        if u > 0.86 and spec.kind not in ("external",):
            emit(sid, "WARN", "cpu_throttle", ms=int(1000 * (u - 0.8)))
        if u > 0.9 and spec.kind == "datastore":
            emit(sid, "ERROR", "pool_exhausted", q=int(200 * (u - 0.85) * 20))
        for dep in spec.deps:
            if frame.get(dep, {}).get("error_rate", 0) > 35 and rng.random() < 0.4:
                emit(sid, "WARN", "circuit_open", dep=dep,
                     n=int(min(20, frame[dep]["error_rate"] / 5)))
        if rng.random() < 0.25:
            emit(sid, "INFO", "http_5xx", code=200, route=rng.choice(ROUTES),
                 ms=int(m["latency_p50"]))
    return out


def to_dict(l: LogLine) -> dict:
    return asdict(l)
