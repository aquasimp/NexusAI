"""Causal queueing-network telemetry simulator.

Design contract
---------------
Only ROOT faults are injected. All observable symptoms on other services are
*derived* from the dependency graph:

    utilization u = demand / capacity
    self latency  = service_time / (1 - min(u, 0.985))          [M/M/1 delay]
    latency       = self + Σ fanout · downstream_latency
    timeout err   = σ((p95 - timeout) / 0.14·timeout)
    demand        = Σ caller_rps · fanout · (1 + retry_amplification)

Retries on downstream failure raise downstream demand -> raises u -> raises
latency -> raises timeout errors. That feedback loop is what produces
cascading failures without any cascade being scripted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .topology import EVAL_ORDER, METRICS, SERVICES, callers_of

DAY = 86400.0


@dataclass
class Fault:
    """A root-cause fault injected into the world."""
    id: str
    target: str
    kind: str        # service_time_mult | error_add | mem_leak | traffic_mult
                     # | util_add | hard_fail | capacity_mult | cache_miss
    magnitude: float
    start_tick: int
    ramp_ticks: int = 8
    profile: str = "ramp"          # step | ramp | exp
    cleared_tick: int | None = None
    decay_ticks: int = 14
    meta: dict = field(default_factory=dict)

    def intensity(self, t: int) -> float:
        if t < self.start_tick:
            return 0.0
        if self.cleared_tick is not None and t >= self.cleared_tick:
            k = (t - self.cleared_tick) / max(1, self.decay_ticks)
            return self.magnitude * max(0.0, 1.0 - k) * self._shape(self.cleared_tick)
        return self.magnitude * self._shape(t)

    def _shape(self, t: int) -> float:
        e = t - self.start_tick
        if self.profile == "step":
            return 1.0
        if self.profile == "exp":
            return 1.0 - math.exp(-e / max(1.0, self.ramp_ticks / 2))
        return min(1.0, e / max(1.0, self.ramp_ticks))


@dataclass
class Deploy:
    tick: int
    service: str
    version: str
    author: str
    change: str
    risk: str


class Engine:
    """Deterministic given (seed). Produces one telemetry frame per tick."""

    def __init__(self, seed: int = 7, tick_seconds: float = 15.0,
                 start_hour: float = 9.25, base_rps: float = 1450.0):
        self.rng = np.random.default_rng(seed)
        self.dt = tick_seconds
        self.t = 0
        self.start_hour = start_hour
        self.base_rps = base_rps

        self.faults: list[Fault] = []
        self.deploys: list[Deploy] = []
        self.mitigations: dict[str, set[str]] = {s: set() for s in SERVICES}
        self.replica_scale: dict[str, float] = {s: 1.0 for s in SERVICES}
        self.leak: dict[str, float] = {s: 0.0 for s in SERVICES}
        self._noise: dict[tuple[str, str], float] = {
            (s, m): 0.0 for s in SERVICES for m in METRICS
        }
        self._traffic_noise = 0.0
        self.last_frame: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------ time
    def sim_time(self, t: int | None = None) -> float:
        t = self.t if t is None else t
        return self.start_hour * 3600.0 + t * self.dt

    def diurnal(self, t: int) -> float:
        tod = (self.sim_time(t) % DAY) / DAY
        return (1.0
                + 0.34 * math.sin(2 * math.pi * (tod - 0.30))
                + 0.11 * math.sin(4 * math.pi * (tod - 0.12))
                + 0.04 * math.sin(6 * math.pi * tod))

    # ---------------------------------------------------------------- faults
    def inject(self, fault: Fault) -> Fault:
        self.faults.append(fault)
        return fault

    def add_deploy(self, dep: Deploy) -> None:
        self.deploys.append(dep)

    def fault_value(self, service: str, kind: str) -> float:
        return sum(f.intensity(self.t) for f in self.faults
                   if f.target == service and f.kind == kind)

    def clear_faults(self, service: str | None = None, kinds: tuple[str, ...] = (),
                     by: str = "remediation") -> list[str]:
        cleared = []
        for f in self.faults:
            if f.cleared_tick is not None:
                continue
            if service and f.target != service:
                continue
            if kinds and f.kind not in kinds:
                continue
            f.cleared_tick = self.t
            f.meta["cleared_by"] = by
            cleared.append(f.id)
        return cleared

    def active_faults(self) -> list[Fault]:
        return [f for f in self.faults if f.intensity(self.t) > 1e-6]

    # ------------------------------------------------------------------ tick
    def _ar(self, key, sigma: float, rho: float = 0.86) -> float:
        v = rho * self._noise[key] + math.sqrt(1 - rho ** 2) * self.rng.normal(0, sigma)
        self._noise[key] = v
        return v

    def tick(self) -> dict[str, dict[str, float]]:
        t = self.t
        self._traffic_noise = 0.9 * self._traffic_noise + 0.1 * self.rng.normal(0, 0.05)

        traffic_mult = 1.0 + self.fault_value("api-gateway", "traffic_mult")
        external_rps = max(
            50.0,
            self.base_rps * self.diurnal(t) * traffic_mult * (1 + self._traffic_noise),
        )

        demand: dict[str, float] = {s: 0.0 for s in SERVICES}
        demand["api-gateway"] = external_rps
        frame: dict[str, dict[str, float]] = {}

        # --- pass 1: propagate demand downward (callers before callees) ----
        for sid in reversed(EVAL_ORDER):
            spec = SERVICES[sid]
            for dep, fanout in spec.deps.items():
                dspec = SERVICES[dep]
                prev_dep = self.last_frame.get(dep, {})
                dep_err = prev_dep.get("error_rate", dspec.base_error_pct) / 100.0
                amp = 1.0
                if "circuit_breaker" not in self.mitigations[sid]:
                    amp += dspec.retry_policy * dep_err * 1.6
                miss = 1.0
                if dspec.kind == "cache":
                    miss = 1.0 + self.fault_value(dep, "cache_miss")
                demand[dep] += demand[sid] * fanout * amp * miss

        # --- pass 2: resolve latency/errors upward (callees first) ---------
        for sid in EVAL_ORDER:
            spec = SERVICES[sid]
            rps = max(1.0, demand[sid] * (1 + self._ar((sid, "rps"), 0.012)))

            cap_mult = self.replica_scale[sid] * max(
                0.05, 1.0 - self.fault_value(sid, "capacity_mult"))
            capacity = spec.replicas * spec.rps_per_replica * cap_mult
            u = min(0.995, rps / capacity + self.fault_value(sid, "util_add"))

            # memory: baseline + utilization pressure + accumulated leak
            leak_rate = self.fault_value(sid, "mem_leak")
            if leak_rate > 0:
                self.leak[sid] += leak_rate * self.dt / 60.0
            elif self.leak[sid] > 0:
                self.leak[sid] = max(0.0, self.leak[sid] - 0.35)
            mem = spec.base_mem_pct + 9.0 * u + self.leak[sid] \
                + self._ar((sid, "mem"), 0.35)
            mem = float(np.clip(mem, 2.0, 99.5))

            st = spec.base_service_time_ms * (1.0 + self.fault_value(sid, "service_time_mult"))
            if mem > 88.0:                       # GC / swap pressure
                st *= 1.0 + (mem - 88.0) * 0.16
            if "query_optimized" in self.mitigations[sid]:
                st *= 0.55

            self_lat = st / max(0.015, 1.0 - min(u, 0.985))
            down_lat = sum(
                f * frame[d]["latency_p50"] * (0.25 if "circuit_breaker" in
                                               self.mitigations[sid] else 1.0)
                for d, f in spec.deps.items()
            )
            p50 = (self_lat + down_lat) * (1 + self._ar((sid, "latency_p50"), 0.02))
            tail = 1.85 + 1.30 * (u ** 2) + 0.5 * min(1.0, down_lat / max(1e-6, p50))
            p95 = p50 * tail * math.exp(self._ar((sid, "latency_p95"), 0.05))

            # errors: baseline + injected + timeout-induced + inherited
            err = spec.base_error_pct + 100.0 * self.fault_value(sid, "hard_fail")
            err += self.fault_value(sid, "error_add")
            if p95 > 0.6 * spec.timeout_ms:
                err += 92.0 / (1.0 + math.exp(-(p95 - spec.timeout_ms) / (0.10 * spec.timeout_ms)))
            for d, f in spec.deps.items():
                dspec = SERVICES[d]
                inherited = frame[d]["error_rate"] * min(1.0, f)
                absorbed = 0.42 if (spec.retry_policy > 0 or dspec.retry_policy > 0) else 0.0
                if "circuit_breaker" in self.mitigations[sid]:
                    absorbed = 0.86
                if "fallback_cache" in self.mitigations[sid]:
                    absorbed = max(absorbed, 0.78)
                err += inherited * (1 - absorbed)
            err = float(np.clip(err + abs(self._ar((sid, "error_rate"), 0.01)), 0.0, 100.0))

            cpu = float(np.clip(94.0 * u + 4.0 + self._ar((sid, "cpu"), 0.9), 1.0, 99.9))
            if spec.kind == "external":
                cpu, mem = 0.0, 0.0

            frame[sid] = {
                "rps": round(rps, 2), "latency_p50": round(max(0.05, p50), 3),
                "latency_p95": round(max(0.1, p95), 3), "error_rate": round(err, 4),
                "cpu": round(cpu, 2), "mem": round(mem, 2),
                "utilization": round(u, 4), "replicas": spec.replicas * self.replica_scale[sid],
            }

            # OOM restart: sheds memory, spikes errors for a tick
            if mem > 97.5 and self.rng.random() < 0.45:
                self.leak[sid] = max(0.0, self.leak[sid] - 34.0)
                frame[sid]["error_rate"] = min(100.0, frame[sid]["error_rate"] + 11.0)
                frame[sid]["oom_restart"] = 1.0

        self.last_frame = frame
        self.t += 1
        return frame

    # ------------------------------------------------------------ remediation
    def apply_action(self, action_id: str, target: str) -> dict:
        """Mutates the world. Returns what actually changed (may be nothing)."""
        changed: dict = {"action": action_id, "target": target, "effects": []}
        if action_id == "rollback_deploy":
            c = self.clear_faults(target, ("service_time_mult", "error_add",
                                           "capacity_mult"), by=action_id)
            changed["effects"] = [f"cleared_faults={c}"]
        elif action_id == "restart_workload":
            self.leak[target] = 0.0
            c = self.clear_faults(target, ("mem_leak",), by=action_id)
            changed["effects"] = ["memory_reclaimed", f"cleared_faults={c}"]
        elif action_id == "scale_out":
            self.replica_scale[target] = min(4.0, self.replica_scale[target] * 2.0)
            changed["effects"] = [f"replica_scale={self.replica_scale[target]}"]
        elif action_id == "enable_circuit_breaker":
            for clr in callers_of(target):
                self.mitigations[clr].add("circuit_breaker")
            changed["effects"] = [f"breaker_on={callers_of(target)}"]
        elif action_id == "enable_fallback_cache":
            for clr in callers_of(target):
                self.mitigations[clr].add("fallback_cache")
            changed["effects"] = [f"fallback_on={callers_of(target)}"]
        elif action_id == "kill_blocking_queries":
            c = self.clear_faults(target, ("service_time_mult", "util_add"), by=action_id)
            self.mitigations[target].add("query_optimized")
            changed["effects"] = [f"cleared_faults={c}", "lock_contention_released"]
        elif action_id == "flush_and_warm_cache":
            c = self.clear_faults(target, ("cache_miss", "service_time_mult"), by=action_id)
            changed["effects"] = [f"cleared_faults={c}"]
        elif action_id == "throttle_ingress":
            c = self.clear_faults("api-gateway", ("traffic_mult",), by=action_id)
            changed["effects"] = [f"shed_load cleared={c}"]
        elif action_id == "no_op_observe":
            changed["effects"] = ["observation_only"]
        else:
            changed["effects"] = ["unknown_action:no_change"]
        return changed
