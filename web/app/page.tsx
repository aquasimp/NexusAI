import Link from "next/link";

const PILLARS = [
  ["Causal simulation, not animation",
   "A queueing-network model of nine services. Only the root fault is injected — every downstream symptom is derived from utilization, timeout budgets and retry amplification, so cascades emerge from the graph."],
  ["Statistics before LLMs",
   "Harmonic seasonal baselines, AR(1) whitening, shrinkage-covariance Mahalanobis distance and IsolationForest fused into one calibrated score with a k-of-n persistence gate."],
  ["Evidence-ranked root cause",
   "A trained multinomial classifier over 30 incident features ranks seven causes and exposes per-feature contributions. The LLM narrates and critiques; it never invents the verdict."],
  ["Measured, not asserted",
   "A benchmark harness replays labelled episodes and computes detection F1, localization top-k, root-cause accuracy under grouped CV, retrieval nDCG and latency. Every published number is generated at run time."],
];

export default function Landing() {
  return (
    <div className="relative z-10">
      <header className="mx-auto flex h-16 max-w-[1200px] items-center px-6">
        <span className="flex items-center gap-2.5">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-gradient-to-br
            from-[#35e0d0] to-[#4c8dff] text-[11px] font-bold text-[#04121a]">N</span>
          <span className="text-[13px] font-semibold">NEXUS<span className="text-[--color-cyan]">AI</span></span>
        </span>
        <Link href="/architecture" className="ml-auto text-[12px] text-[--color-mute] hover:text-white">
          How it works
        </Link>
      </header>

      <section className="mx-auto max-w-[1200px] px-6 pt-20 pb-14">
        <span className="chip text-[--color-cyan]" style={{ borderColor: "#35e0d033" }}>
          <span className="h-1.5 w-1.5 rounded-full bg-[--color-cyan]" />
          Autonomous incident intelligence
        </span>
        <h1 className="mt-6 max-w-3xl text-[52px] font-semibold leading-[1.04] tracking-[-0.03em]">
          <span className="gradient-text">Find the cause</span><br />
          before the pager finishes ringing.
        </h1>
        <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-[--color-mute]">
          NEXUS watches a live service mesh, detects statistically abnormal behaviour,
          localizes the fault across the dependency graph, ranks root-cause hypotheses
          against retrieved runbooks, quantifies SLO and revenue impact, and proposes a
          remediation behind a human-approval gate — then verifies whether the system
          actually recovered.
        </p>
        <div className="mt-9 flex flex-wrap items-center gap-3">
          <Link href="/command"
            className="rounded-lg bg-gradient-to-b from-[#3ddccb] to-[#22b6c9] px-5 py-2.5
              text-[13px] font-semibold text-[#04121a] transition hover:brightness-110">
            Launch demo →
          </Link>
          <Link href="/evaluation"
            className="rounded-lg border border-[--color-line] px-5 py-2.5 text-[13px]
              text-[--color-ink] hover:bg-white/5">
            See the benchmark
          </Link>
          <span className="text-[11px] text-[--color-mute]">
            Runs fully local · no API key required
          </span>
        </div>
      </section>

      <div className="hairline mx-auto max-w-[1200px]" />

      <section className="mx-auto grid max-w-[1200px] gap-px overflow-hidden px-6 py-16
                          sm:grid-cols-2">
        {PILLARS.map(([t, b]) => (
          <div key={t} className="p-6">
            <h3 className="text-[13.5px] font-medium tracking-tight">{t}</h3>
            <p className="mt-2.5 text-[12.5px] leading-relaxed text-[--color-mute]">{b}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-[1200px] px-6 pb-24">
        <div className="panel p-6">
          <div className="kicker">Honest scope</div>
          <p className="mt-2 max-w-3xl text-[12.5px] leading-relaxed text-[--color-mute]">
            The telemetry, logs and remediation effects are <strong className="text-[--color-amber]">simulated</strong>.
            The detection, localization, feature extraction, classification, retrieval,
            impact model, policy engine, agent loop and every evaluation metric are
            <strong className="text-[--color-lime]"> real</strong> and would run unchanged
            against production telemetry. Each panel in the product carries its own
            provenance badge, and the Architecture page lists exactly what a production
            deployment would have to replace.
          </p>
        </div>
      </section>
    </div>
  );
}
