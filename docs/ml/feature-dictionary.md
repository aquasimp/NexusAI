# NEXUS AI 35-Feature Dictionary

The RCA classification model uses 35 strictly class-agnostic features extracted from telemetry windows:

| Index | Feature Name | Description | Type |
|---|---|---|---|
| 0 | `leader_kind_edge` | True if blamed root service is an edge gateway | Binary |
| 1 | `leader_kind_app` | True if blamed root service is an application microservice | Binary |
| 2 | `leader_kind_datastore` | True if blamed root service is a primary database | Binary |
| 3 | `leader_kind_cache` | True if blamed root service is an in-memory cache | Binary |
| 4 | `leader_kind_external` | True if blamed root service is a third-party SaaS API | Binary |
| 5 | `leader_z_rps` | Peak z-score of request rate on leader | Float |
| 6 | `leader_z_p50` | Peak z-score of median latency on leader | Float |
| 7 | `leader_z_p95` | Peak z-score of 95th percentile latency on leader | Float |
| 8 | `leader_z_err` | Peak z-score of error percentage on leader | Float |
| 9 | `leader_z_cpu` | Peak z-score of CPU utilization on leader | Float |
| 10 | `leader_z_mem` | Peak z-score of memory utilization on leader | Float |
| 11 | `leader_mem_slope` | OLS trend slope of memory time series | Float |
| 12 | `leader_mem_tau` | Mann-Kendall rank correlation of memory progression | Float [-1, 1] |
| 13 | `leader_err_slope` | OLS trend slope of error rate | Float |
| 14 | `leader_p95_slope` | OLS trend slope of p95 latency | Float |
| 15 | `entry_z_rps` | Peak z-score of external ingress RPS at api-gateway | Float |
| 16 | `anomalous_fraction` | Proportion of microservices simultaneously anomalous | Float [0, 1] |
| 17 | `onset_spread_norm` | Normalized duration between earliest and latest service anomalies | Float [0, 1] |
| 18 | `leader_lead_norm` | Normalized time by which leader preceded other anomalies | Float [0, 1] |
| 19 | `deploy_recent` | True if any deployment occurred within the last 60 ticks | Binary |
| 20 | `deploy_on_leader` | True if deployment occurred directly on blamed leader | Binary |
| 21 | `err_dominance` | Error peak relative to error + latency peaks | Float [0, 1] |
| 22 | `lat_dominance` | Latency peak relative to error + latency peaks | Float [0, 1] |
| 23 | `sat_index` | Saturation proxy: tanh(CPU * RPS / 40.0) | Float |
| 24 | `external_err_share` | Fraction of total system errors originating in external tier | Float [0, 1] |
| 25 | `p95_slo_ratio` | Leader p95 divided by its configured SLO target | Float |
| 26 | `err_slo_ratio` | Leader error rate divided by its configured SLO target | Float |
| 27 | `log_timeout` | Relative frequency of timeout logs | Float [0, 1] |
| 28 | `log_lock_wait` | Relative frequency of database lock wait logs | Float [0, 1] |
| 29 | `log_oom` | Relative frequency of out-of-memory logs | Float [0, 1] |
| 30 | `log_schema_reject` | Relative frequency of schema validation rejection logs | Float [0, 1] |
| 31 | `log_pool_exhausted` | Relative frequency of connection pool exhausted logs | Float [0, 1] |
| 32 | `log_cache_miss` | Relative frequency of cache miss logs | Float [0, 1] |
| 33 | `log_circuit_open` | Relative frequency of circuit breaker open logs | Float [0, 1] |
| 34 | `log_slow_query` | Relative frequency of slow database query logs | Float [0, 1] |
