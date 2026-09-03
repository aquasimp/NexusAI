"""Reproducible incident scenarios. Each defines ONE root fault (+ optional
deploy event). Ground-truth labels here are the *only* labels used by the
benchmark — the runtime pipeline never sees them."""
from __future__ import annotations
from dataclasses import dataclass

from .engine import Deploy, Engine, Fault


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    blurb: str
    root_service: str          # ground truth
    root_class: str            # ground truth RCA class
    gold_actions: tuple[str, ...]
    gold_docs: tuple[str, ...]
    severity: str


SCENARIOS: dict[str, Scenario] = {
    "db_latency_spike": Scenario(
        "db_latency_spike", "Database latency spike",
        "Long-running analytics transaction holds row locks on the primary; "
        "query service time inflates and connection pools back up.",
        "postgres-primary", "db_latency_saturation",
        ("kill_blocking_queries",), ("rb-postgres-latency", "rb-connection-pool"), "SEV2"),
    "bad_deploy": Scenario(
        "bad_deploy", "Failed deployment",
        "payment-service v2026.8.14 ships an N+1 query and a null-guard "
        "regression; latency and 5xx step-change at the deploy boundary.",
        "payment-service", "bad_deploy",
        ("rollback_deploy",), ("rb-deploy-rollback", "rb-payment-oncall"), "SEV1"),
    "memory_leak": Scenario(
        "memory_leak", "Memory leak",
        "Unbounded in-process feature cache in recommendation-service grows "
        "until GC thrash and OOM restarts appear.",
        "recommendation-service", "memory_leak",
        ("restart_workload",), ("rb-memory-leak", "rb-jvm-gc"), "SEV3"),
    "traffic_surge": Scenario(
        "traffic_surge", "Traffic surge",
        "Marketing push drives 3.2x ingress; edge and tier-1 utilization "
        "crosses the queueing knee.",
        "api-gateway", "traffic_surge",
        ("scale_out", "throttle_ingress"), ("rb-capacity-surge", "rb-autoscaling"), "SEV2"),
    "dependency_outage": Scenario(
        "dependency_outage", "Third-party dependency outage",
        "Stripe API returns hard failures and timeouts; payment errors "
        "propagate to the gateway.",
        "stripe-api", "dependency_outage",
        ("enable_circuit_breaker",), ("rb-third-party-outage", "rb-circuit-breaker"), "SEV1"),
    "api_error_explosion": Scenario(
        "api_error_explosion", "API error explosion",
        "A gateway route/schema config push rejects valid requests: 5xx rate "
        "explodes while latency and CPU stay flat.",
        "api-gateway", "api_error_explosion",
        ("rollback_deploy",), ("rb-error-spike", "rb-config-rollback"), "SEV1"),
    "cascading_failure": Scenario(
        "cascading_failure", "Cascading failure",
        "Redis eviction storm raises miss rate; three dependent services "
        "amplify load via retries until the gateway saturates.",
        "redis-cache", "cascading_failure",
        ("flush_and_warm_cache", "enable_fallback_cache"),
        ("rb-redis-eviction", "rb-cascade-containment"), "SEV1"),
}


def arm(engine: Engine, scenario_id: str, at_tick: int | None = None,
        rng_jitter: float = 1.0) -> Scenario:
    """Inject `scenario_id` into `engine`. Returns the scenario (ground truth)."""
    sc = SCENARIOS[scenario_id]
    t0 = engine.t + 2 if at_tick is None else at_tick
    j = rng_jitter

    if scenario_id == "db_latency_spike":
        engine.inject(Fault("f-db-lock", "postgres-primary", "service_time_mult",
                            22.0 * j, t0, ramp_ticks=10, profile="ramp"))
        engine.inject(Fault("f-db-util", "postgres-primary", "util_add",
                            0.26 * j, t0, ramp_ticks=10))
    elif scenario_id == "bad_deploy":
        engine.add_deploy(Deploy(t0, "payment-service", "v2026.8.14-rc2",
                                 "m.okafor", "feat: split settlement ledger writes", "high"))
        engine.inject(Fault("f-deploy-st", "payment-service", "service_time_mult",
                            2.4 * j, t0, ramp_ticks=2, profile="step"))
        engine.inject(Fault("f-deploy-err", "payment-service", "error_add",
                            5.2 * j, t0, ramp_ticks=2, profile="step"))
    elif scenario_id == "memory_leak":
        engine.inject(Fault("f-leak", "recommendation-service", "mem_leak",
                            0.85 * j, t0, ramp_ticks=4, profile="step"))
    elif scenario_id == "traffic_surge":
        engine.inject(Fault("f-surge", "api-gateway", "traffic_mult",
                            2.2 * j, t0, ramp_ticks=14, profile="exp"))
    elif scenario_id == "dependency_outage":
        engine.inject(Fault("f-stripe", "stripe-api", "hard_fail",
                            0.74 * j, t0, ramp_ticks=3, profile="ramp"))
        engine.inject(Fault("f-stripe-lat", "stripe-api", "service_time_mult",
                            22.0 * j, t0, ramp_ticks=3))
    elif scenario_id == "api_error_explosion":
        engine.add_deploy(Deploy(t0, "api-gateway", "cfg-2026.08.14.3",
                                 "r.singh", "chore: tighten request schema validation", "medium"))
        engine.inject(Fault("f-cfg", "api-gateway", "error_add",
                            27.0 * j, t0, ramp_ticks=2, profile="step"))
    elif scenario_id == "cascading_failure":
        engine.inject(Fault("f-evict", "redis-cache", "cache_miss",
                            2.6 * j, t0, ramp_ticks=9, profile="exp"))
        engine.inject(Fault("f-evict-st", "redis-cache", "service_time_mult",
                            7.0 * j, t0, ramp_ticks=9, profile="exp"))
    else:
        raise KeyError(scenario_id)
    return sc
