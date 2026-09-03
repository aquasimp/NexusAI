// about/page.tsx
import { Panel } from "@/components/ui";

const STACK = [
  ["Frontend", "Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind v4 · Framer Motion · hand-written SVG charts"],
  ["Backend", "Python 3.12 · FastAPI · asyncio · Server-Sent Events · SQLite · Pydantic Settings"],
  ["ML / stats", "NumPy · SciPy · scikit-learn (LedoitWolf, IsolationForest, LogisticRegression, TruncatedSVD, GroupKFold) · custom harmonic regression, AR(1) whitening, CUSUM, BM25"],
  ["AI layer", "Provider-agnostic LLM client (OpenAI · Anthropic · Ollama · deterministic) · typed tool registry · schema-validated structured output"],
];

const DECISIONS = [
  ["Causal simulator instead of a scripted timeline",
   "Scripted demos make the AI layer untestable: if symptoms are authored, correct answers are authored too. A queueing model with only root-fault injection turns every demo run into a genuine inference problem and lets the benchmark generate unlimited labelled episodes."],
  ["Statistics decide, the LLM explains",
   "LLMs are excellent at narrating evidence and poor at being a calibrated classifier over 54 correlated numeric series. Ranking lives in a model I can cross-validate; the LLM gets tools, an evidence packet, and the right to disagree in writing."],
  ["Lexical hybrid retrieval over neural embeddings",
   "On a 60-chunk corpus dense with exact technical tokens, BM25 + LSA fused by RRF measured competitively while adding zero model downloads and staying deterministic. The Evaluation page publishes the retrieval numbers so the trade-off is auditable rather than assumed."],
  ["Independent recovery verification",
   "Any system that proposes fixes must be able to be wrong. Post-remediation the detector re-evaluates for six consecutive clear ticks; a wrong action produces no recovery and the incident escalates. This is the difference between a workflow and a demo."],
  ["Provenance labels in the product, not just the README",
   "Interviewers discount portfolio claims by default. Labelling each panel REAL / SIMULATED / GAP makes the honesty structural."],
];

const CHALLENGES = [
  ["Seasonality was drowning the signal",
   "Raw z-scores fired every morning as traffic ramped. Fixing it took three layers: harmonic regression for time-of-day, AR(1) whitening because residuals were strongly autocorrelated (ρ≈0.85, so naive z-scores were badly over-dispersed), and MAD instead of standard deviation so the fitted scale is not inflated by the very anomalies it should flag."],
  ["Everything looked guilty at once",
   "During a cascade, six services breach simultaneously and the loudest is usually the edge — the victim, not the cause. Adding CUSUM onset ordering plus upstreamness on the anomalous subgraph is what moved localization from 'blames the gateway' to naming the origin."],
  ["The classifier initially cheated",
   "My first feature set included one-hot service identity, which let the model memorise service→label because each scenario has a fixed root service. Generalising to service *kind* and grouping CV folds by episode seed removed the leak; accuracy dropped, and the honest number is the one on the Evaluation page."],
  ["Backpressure on the SSE fan-out",
   "A slow browser tab blocked the simulation loop. The hub now uses bounded queues and drops slow consumers instead of applying backpressure to the world."],
];

export default function About() {
  return (
    <div className="space-y-4">
      <div>
        <div className="kicker">About the project</div>
        <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em]">
          Stack, decisions, and what went wrong first</h1>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel kicker="Technology stack" title="What it is built with">
          <dl className="space-y-3">
            {STACK.map(([k, v]) => (
              <div key={k}>
                <dt className="kicker">{k}</dt>
                <dd className="mt-1 text-[12px] leading-relaxed text-[--color-mute]">{v}</dd>
              </div>))}
          </dl>
        </Panel>
        <Panel kicker="Design decisions" title="And the reasoning behind them">
          <dl className="space-y-3">
            {DECISIONS.map(([k, v]) => (
              <div key={k}>
                <dt className="text-[12px] font-medium">{k}</dt>
                <dd className="mt-1 text-[11.5px] leading-relaxed text-[--color-mute]">{v}</dd>
              </div>))}
          </dl>
        </Panel>
      </div>
      <Panel kicker="Engineering challenges" title="Problems that actually cost time">
        <dl className="grid gap-4 sm:grid-cols-2">
          {CHALLENGES.map(([k, v]) => (
            <div key={k}>
              <dt className="text-[12px] font-medium text-[--color-cyan]">{k}</dt>
              <dd className="mt-1 text-[11.5px] leading-relaxed text-[--color-mute]">{v}</dd>
            </div>))}
        </dl>
      </Panel>
      <Panel kicker="Limitations" title="Stated plainly">
        <p className="text-[12px] leading-relaxed text-[--color-mute]">
          The telemetry is synthetic, so detection and RCA scores measure performance
          against my own generative process — they are an upper bound on real-world
          behaviour, not a prediction of it. The benchmark is small (dozens of episodes
          per configuration), which is why every accuracy carries a Wilson interval.
          Root causes are single-fault; concurrent independent incidents are not modelled.
          The action space is seven discrete remediations, not arbitrary operations. And
          remediation effects are simulated — nothing touches real infrastructure.
        </p>
      </Panel>
    </div>
  );
}
