// architecture/page.tsx
"use client";
import { Panel, Provenance } from "@/components/ui";
import { useApi } from "@/lib/api";

const LAYERS = [
  ["1 · Environment", "SIMULATED",
   "Nine-service queueing network. Demand propagates caller→callee; latency resolves callee→caller as service_time/(1−u) plus fanout-weighted downstream latency. Timeout errors are a logistic function of p95 vs the configured timeout, and retries on failure feed back into downstream demand. Only root faults are injected."],
  ["2 · Detection", "REAL",
   "Per (service, metric): harmonic ridge regression on time-of-day removes seasonality, AR(1) whitening removes autocorrelation, MAD scaling yields robust z-scores. Per service: Ledoit-Wolf shrinkage Mahalanobis distance plus IsolationForest, both mapped to training-percentile space and fused. Threshold is the 99.5th percentile of warm-up scores, gated by 3-of-5 persistence with hysteresis."],
  ["3 · Localization", "REAL",
   "Two-sided CUSUM estimates per-service onset. Blame combines anomaly magnitude, onset lead, upstreamness on the anomalous subgraph, and deploy proximity. Upstreamness is what distinguishes a cause from its victims."],
  ["4 · Root cause", "REAL",
   "Thirty-five class-agnostic incident features (metric z-peaks, Mann-Kendall memory trend, error/latency dominance, saturation index, log-pattern rates, deploy alignment, SLO ratios) feed a multinomial logistic regression trained on seeded episodes with GroupKFold CV. Per-feature coefficient × standardized-value contributions are surfaced as evidence."],
  ["5 · Retrieval", "REAL",
   "BM25 fused with TF-IDF + Truncated SVD via reciprocal rank fusion over a 10-document runbook corpus, with a service-tag boost and one-chunk-per-document dedup. Retrieved documents carry an executable action manifest."],
  ["6 · Agent", "REAL",
   "A bounded tool-calling loop over eight tools that read genuine world state: query_metrics, search_logs, get_deployments, get_topology, search_runbooks, read_runbook, get_blame_ranking, compare_windows. The LLM critiques the ranking and narrates; it cannot originate the verdict. Schema-validated output, deterministic analyst fallback."],
  ["7 · Policy & actuation", "REAL plan / SIMULATED effect",
   "Actions come only from retrieved runbooks. Risk ≥ medium, irreversibility, wide blast radius or SEV1 forces a human approval gate implemented as an asyncio event. Execution mutates the environment's fault objects, then the detector independently verifies recovery — a wrong action leaves the system broken and the incident escalates."],
  ["8 · Evaluation", "REAL",
   "A headless harness replays labelled episodes through the identical code path and computes detection F1/PR-AUC, localization top-k, RCA accuracy and macro-F1 under grouped CV, retrieval recall/MRR/nDCG, joint success and latency percentiles, with Wilson intervals."],
];

export default function Architecture() {
  const { data } = useApi<any>("/system/info");
  return (
    <div className="space-y-4">
      <div>
        <div className="kicker">Architecture</div>
        <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em]">How NEXUS works</h1>
        <p className="mt-2 max-w-3xl text-[12.5px] leading-relaxed text-[--color-mute]">
          Eight layers. The statistics decide; the language model explains. Every layer
          declares whether it is genuine computation, part of the simulated environment,
          or a deliberate production gap.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {LAYERS.map(([t, p, b]) => (
          <Panel key={t} kicker={t} title={undefined}
            right={<Provenance kind={p.startsWith("REAL") ? "REAL" : "SIMULATED"} note={p} />}>
            <p className="text-[12px] leading-relaxed text-[--color-mute]">{b}</p>
          </Panel>))}
      </div>
      {data && (
        <Panel kicker="Runtime configuration" title="Live parameters">
          <pre className="metric overflow-x-auto text-[10.5px] leading-relaxed text-[--color-mute]">
{JSON.stringify({ detector: data.detector, ranker: data.ranker,
  llm: data.llm, knowledge_base: data.knowledge_base,
  provenance: data.provenance }, null, 2)}
          </pre>
        </Panel>)}
    </div>
  );
}
