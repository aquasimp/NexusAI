# Causal Simulation Engine

## Core Mechanics

The NEXUS simulator implements an authentic open queueing network using discrete-time simulation ticks (default: 15.0 simulated seconds per tick).

### Two-Pass Execution Invariant
In every tick:
1. **Pass 1 (Top-Down Demand Propagation)**:
   Evaluated in order of callers before callees (`reversed(EVAL_ORDER)`). Demand starts at `api-gateway` based on diurnal external RPS:
   $$\lambda_{ext}(t) = \text{base\_rps} \cdot \left(1 + 0.35 \sin(2\pi \cdot \text{tod}) - 0.15 \cos(4\pi \cdot \text{tod})\right)$$
   Callers amplify downstream demand when dependencies return errors due to retry policies:
   $$\text{amp} = 1.0 + \text{retry\_policy} \times \text{dep\_error\_rate} \times 1.6$$
2. **Pass 2 (Bottom-Up Latency & Error Resolution)**:
   Evaluated in reverse-topological order (`EVAL_ORDER`), ensuring callees resolve before their callers.
   Service latency follows $M/M/1$ queueing dilation:
   $$\text{self\_lat} = \frac{\text{base\_service\_time}}{1 - u}$$
   where $u = \frac{\lambda}{\text{capacity}}$. Downstream latencies propagate additively along fanout edges.

### Root Injections & Emergent Cascades
Faults are injected exclusively at root causes (e.g., Postgres lock contention, bad container deploy, Redis memory eviction). All caller symptoms (gateway $504$ timeouts, circuit breaker trips, thread pool exhaustions) emerge causally from downstream queue saturation.
