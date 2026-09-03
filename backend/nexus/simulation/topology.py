"""Service topology: a realistic 9-node dependency graph with capacity model."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ServiceSpec:
    id: str
    name: str
    kind: str                 # edge | app | datastore | cache | external
    tier: int
    replicas: int
    rps_per_replica: float
    base_service_time_ms: float
    base_error_pct: float
    base_mem_pct: float
    timeout_ms: float
    slo_p95_ms: float
    slo_error_pct: float
    retry_policy: float       # retries emitted per downstream failure
    deps: dict[str, float] = field(default_factory=dict)   # dep_id -> calls/request
    owner: str = "platform"


SERVICES: dict[str, ServiceSpec] = {
    "api-gateway": ServiceSpec(
        id="api-gateway", name="API Gateway", kind="edge", tier=0,
        replicas=12, rps_per_replica=180, base_service_time_ms=4.0,
        base_error_pct=0.08, base_mem_pct=41, timeout_ms=2500,
        slo_p95_ms=450, slo_error_pct=0.5, retry_policy=0.0,
        deps={"auth-service": 1.0, "payment-service": 0.22,
              "recommendation-service": 0.55, "notification-service": 0.14},
        owner="edge-platform",
    ),
    "auth-service": ServiceSpec(
        id="auth-service", name="Authentication Service", kind="app", tier=1,
        replicas=8, rps_per_replica=150, base_service_time_ms=11.0,
        base_error_pct=0.05, base_mem_pct=38, timeout_ms=800,
        slo_p95_ms=180, slo_error_pct=0.2, retry_policy=0.7,
        deps={"postgres-primary": 0.35, "redis-cache": 1.0},
        owner="identity",
    ),
    "payment-service": ServiceSpec(
        id="payment-service", name="Payment Service", kind="app", tier=1,
        replicas=6, rps_per_replica=70, base_service_time_ms=26.0,
        base_error_pct=0.12, base_mem_pct=46, timeout_ms=4000,
        slo_p95_ms=900, slo_error_pct=0.3, retry_policy=0.4,
        deps={"postgres-primary": 1.4, "stripe-api": 1.0},
        owner="payments",
    ),
    "recommendation-service": ServiceSpec(
        id="recommendation-service", name="Recommendation Service", kind="app", tier=1,
        replicas=10, rps_per_replica=120, base_service_time_ms=19.0,
        base_error_pct=0.09, base_mem_pct=57, timeout_ms=1200,
        slo_p95_ms=350, slo_error_pct=1.0, retry_policy=0.3,
        deps={"redis-cache": 2.2, "postgres-primary": 0.18},
        owner="growth-ml",
    ),
    "notification-service": ServiceSpec(
        id="notification-service", name="Notification Service", kind="app", tier=1,
        replicas=4, rps_per_replica=90, base_service_time_ms=15.0,
        base_error_pct=0.20, base_mem_pct=35, timeout_ms=3000,
        slo_p95_ms=600, slo_error_pct=2.0, retry_policy=1.2,
        deps={"redis-cache": 0.6, "sendgrid-api": 0.9},
        owner="messaging",
    ),
    "postgres-primary": ServiceSpec(
        id="postgres-primary", name="Postgres Primary", kind="datastore", tier=2,
        replicas=1, rps_per_replica=2600, base_service_time_ms=2.4,
        base_error_pct=0.01, base_mem_pct=62, timeout_ms=1500,
        slo_p95_ms=60, slo_error_pct=0.1, retry_policy=0.0,
        deps={}, owner="data-platform",
    ),
    "redis-cache": ServiceSpec(
        id="redis-cache", name="Redis Cache", kind="cache", tier=2,
        replicas=3, rps_per_replica=4200, base_service_time_ms=0.7,
        base_error_pct=0.01, base_mem_pct=54, timeout_ms=250,
        slo_p95_ms=12, slo_error_pct=0.1, retry_policy=0.0,
        deps={}, owner="data-platform",
    ),
    "stripe-api": ServiceSpec(
        id="stripe-api", name="Stripe API (external)", kind="external", tier=3,
        replicas=1, rps_per_replica=9999, base_service_time_ms=118.0,
        base_error_pct=0.15, base_mem_pct=0, timeout_ms=6000,
        slo_p95_ms=800, slo_error_pct=1.0, retry_policy=0.0,
        deps={}, owner="third-party",
    ),
    "sendgrid-api": ServiceSpec(
        id="sendgrid-api", name="SendGrid API (external)", kind="external", tier=3,
        replicas=1, rps_per_replica=9999, base_service_time_ms=95.0,
        base_error_pct=0.30, base_mem_pct=0, timeout_ms=8000,
        slo_p95_ms=900, slo_error_pct=2.0, retry_policy=0.0,
        deps={}, owner="third-party",
    ),
}

ENTRYPOINT = "api-gateway"
METRICS = ("rps", "latency_p50", "latency_p95", "error_rate", "cpu", "mem")

# business weight used by the impact model (revenue-per-request proxy, USD)
REVENUE_PER_REQ = {
    "payment-service": 0.42, "api-gateway": 0.06,
    "recommendation-service": 0.015, "auth-service": 0.01,
    "notification-service": 0.002,
}


def eval_order() -> list[str]:
    """Reverse-topological order: dependencies resolved before their callers."""
    seen: dict[str, int] = {}

    def depth(sid: str, stack: frozenset[str] = frozenset()) -> int:
        if sid in seen:
            return seen[sid]
        if sid in stack:                      # defensive: cycle guard
            return 0
        d = 0
        for dep in SERVICES[sid].deps:
            d = max(d, depth(dep, stack | {sid}) + 1)
        seen[sid] = d
        return d

    for s in SERVICES:
        depth(s)
    return sorted(SERVICES, key=lambda s: seen[s])


def callers_of(sid: str) -> list[str]:
    return [s for s, spec in SERVICES.items() if sid in spec.deps]


def dependents_transitive(sid: str) -> set[str]:
    """All services that (transitively) depend on `sid`."""
    out: set[str] = set()
    frontier = [sid]
    while frontier:
        cur = frontier.pop()
        for c in callers_of(cur):
            if c not in out:
                out.add(c)
                frontier.append(c)
    return out


EVAL_ORDER = eval_order()
EDGES = [(s, d, f) for s, spec in SERVICES.items() for d, f in spec.deps.items()]
