"use client";
import { useState } from "react";
import { Btn, Empty, Panel, Provenance, Stat } from "@/components/ui";
import { api, fmt, useApi } from "@/lib/api";

export default function Evaluation() {
  const { data, loading, reload } = useApi<any>("/evaluation");
  const [running, setRunning] = useState(false);

  const runIt = async () => {
    setRunning(true);
    try { await api("/evaluation/run", { method: "POST", body: JSON.stringify({ seeds: 4, clean: 8 }) }); reload(); }
    finally { setRunning(false); }
  };

  if (loading) return <div className="skeleton h-[420px] rounded-xl" />;
  if (!data?.available) return (
    <Empty title="No benchmark run on record" body={data?.message ?? ""}
      action={<Btn onClick={runIt} disabled={running}>
        {running ? "Running episodes… (~1–3 min)" : "Run benchmark now"}</Btn>} />
  );

  const r = data.run, d = r.detection, l = r.localization,
    rc = r.root_cause, ret = r.retrieval, inv = r.investigation;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="kicker">Evaluation</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em]">
            Benchmark results</h1>
          <p className="metric mt-1 text-[10.5px] text-[--color-dim]">
            run {r.run_id} · {new Date(r.created_at * 1000).toLocaleString()} ·
            {" "}{r.config.seeds_per_scenario} seeds × 7 scenarios +
            {" "}{r.config.clean_episodes} clean episodes
          </p>
        </div>
        <Btn variant="ghost" onClick={runIt} disabled={running}>
          {running ? "Running…" : "Re-run benchmark"}</Btn>
      </div>

      <div className="rounded-xl border border-[#64e08a33] bg-[#64e08a0a] p-3.5">
        <p className="text-[11.5px] leading-relaxed text-[--color-mute]">
          <strong className="text-[--color-lime]">Provenance:</strong> {r.honesty}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Panel kicker="Anomaly detection" title="Episode-level" right={<Provenance kind="REAL" />}>
          <Stat label="F1" value={fmt.n(d.f1, 3)} />
          <div className="metric mt-3 space-y-1 text-[11px] text-[--color-mute]">
            <div>precision {d.precision} · recall {d.recall}</div>
            <div>recall CI95 {fmt.ci(d.recall_ci95)}</div>
            <div>PR-AUC {d.pr_auc} · specificity {d.specificity}</div>
            <div>FP / clean episode {d.false_positive_rate_per_clean_episode}</div>
            <div>median detect delay {fmt.n(d.detection_delay_s.p50_ms, 0)}s sim</div>
          </div>
        </Panel>
        <Panel kicker="Fault localization" title="Root service" right={<Provenance kind="REAL" />}>
          <Stat label="top-1" value={fmt.pct(l.top1_accuracy)} />
          <div className="metric mt-3 space-y-1 text-[11px] text-[--color-mute]">
            <div>top-2 {fmt.pct(l.top2_accuracy)} · top-3 {fmt.pct(l.top3_accuracy)}</div>
            <div>top-1 CI95 {fmt.ci(l.top1_ci95)}</div>
            <div>n = {l.n} detected episodes</div>
          </div>
        </Panel>
        <Panel kicker="Root cause" title="7-class, grouped CV" right={<Provenance kind="REAL" />}>
          <Stat label="accuracy" value={fmt.pct(rc.learned_accuracy)} />
          <div className="metric mt-3 space-y-1 text-[11px] text-[--color-mute]">
            <div>macro-F1 {rc.macro_f1}</div>
            <div>CI95 {fmt.ci(rc.learned_accuracy_ci95)}</div>
            <div>rule baseline {fmt.pct(rc.rule_baseline_accuracy)}</div>
            <div className="text-[10px]">{rc.cv_scheme}</div>
          </div>
        </Panel>
        <Panel kicker="Retrieval" title="Against gold runbooks" right={<Provenance kind="REAL" />}>
          <Stat label="recall@3 (end-to-end)" value={fmt.pct(ret.predicted_class_query["recall@3"])} />
          <div className="metric mt-3 space-y-1 text-[11px] text-[--color-mute]">
            <div>nDCG@3 {ret.predicted_class_query["ndcg@3"]} · MRR {ret.predicted_class_query.mrr}</div>
            <div>oracle-query recall@3 {fmt.pct(ret.oracle_class_query["recall@3"])}</div>
            <div>{ret.corpus.documents} docs · {ret.corpus.chunks} chunks</div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel kicker="End-to-end" title="Joint investigation success"
          right={<Provenance kind="REAL" />}>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="joint success" value={fmt.pct(inv.joint_success_rate)}
              hint={`CI95 ${fmt.ci(inv.joint_success_ci95)}`} />
            <Stat label="remediation action" value={fmt.pct(inv.remediation_action_accuracy)}
              hint={`CI95 ${fmt.ci(inv.remediation_ci95)}`} />
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-[--color-mute]">{inv.definition}</p>
        </Panel>

        <Panel kicker="Latency" title="Pipeline cost" right={<Provenance kind="REAL" />}>
          <table className="w-full text-left text-[11px]">
            <thead className="kicker"><tr className="border-b border-[--color-line-soft]">
              {["Stage", "n", "mean", "p50", "p95", "max"].map((h) =>
                <th key={h} className="py-1.5 pr-3 font-normal">{h}</th>)}
            </tr></thead>
            <tbody className="metric">
              {Object.entries(r.latency).filter(([, v]: any) => v?.n).map(([k, v]: any) => (
                <tr key={k} className="border-b border-[--color-line-soft] last:border-0">
                  <td className="py-1.5 pr-3 font-sans">{k.replace(/_/g, " ")}</td>
                  <td className="py-1.5 pr-3">{v.n}</td>
                  <td className="py-1.5 pr-3">{fmt.ms(v.mean_ms)}</td>
                  <td className="py-1.5 pr-3">{fmt.ms(v.p50_ms)}</td>
                  <td className="py-1.5 pr-3">{fmt.ms(v.p95_ms)}</td>
                  <td className="py-1.5">{fmt.ms(v.max_ms)}</td>
                </tr>))}
            </tbody>
          </table>
          <p className="mt-2.5 text-[10.5px] text-[--color-dim]">{r.latency.note}</p>
        </Panel>
      </div>

      {rc.confusion_matrix && (
        <Panel kicker="Diagnostics" title="Confusion matrix (rows = truth)"
          right={<Provenance kind="REAL" />}>
          <div className="overflow-x-auto">
            <table className="text-[10.5px]">
              <thead><tr><th /> {rc.classes.map((c: string) => (
                <th key={c} className="kicker px-2 pb-2 font-normal"
                  style={{ writingMode: "vertical-rl" }}>{c}</th>))}</tr></thead>
              <tbody>
                {rc.confusion_matrix.map((row: number[], i: number) => (
                  <tr key={i}>
                    <td className="kicker whitespace-nowrap pr-3">{rc.classes[i]}</td>
                    {row.map((v, j) => {
                      const tot = row.reduce((a, b) => a + b, 0) || 1;
                      return (
                        <td key={j} className="metric px-2 py-1 text-center"
                          style={{ background: v
                            ? `rgba(${i === j ? "100,224,138" : "255,93,115"},${(v / tot) * 0.55})`
                            : undefined, borderRadius: 4 }}>{v || ""}</td>);
                    })}
                  </tr>))}
              </tbody>
            </table>
          </div>
          {rc.calibration_bins?.length > 0 && (
            <div className="mt-4">
              <div className="kicker mb-1.5">Calibration — predicted confidence vs empirical accuracy</div>
              <div className="metric flex flex-wrap gap-3 text-[10.5px] text-[--color-mute]">
                {rc.calibration_bins.map((b: any) => (
                  <span key={b.bin}>{b.bin}: {fmt.pct(b.empirical_accuracy)} (n={b.n})</span>))}
              </div>
            </div>)}
        </Panel>
      )}

      <Panel kicker="Per-scenario" title="Localization by fault type" right={<Provenance kind="REAL" />}>
        <table className="w-full text-left text-[11px]">
          <thead className="kicker"><tr className="border-b border-[--color-line-soft]">
            {["Scenario", "root service", "root class", "top-1", "top-3", "n"].map((h) =>
              <th key={h} className="py-1.5 pr-3 font-normal">{h}</th>)}
          </tr></thead>
          <tbody className="metric">
            {Object.entries(l.per_scenario).map(([k, v]: any) => (
              <tr key={k} className="border-b border-[--color-line-soft] last:border-0">
                <td className="py-1.5 pr-3 font-sans">{r.scenarios[k].title}</td>
                <td className="py-1.5 pr-3">{r.scenarios[k].root_service}</td>
                <td className="py-1.5 pr-3 text-[--color-mute]">{r.scenarios[k].root_class}</td>
                <td className="py-1.5 pr-3" style={{ color: v.top1 === 1 ? "#64e08a" : "#ffb642" }}>
                  {fmt.pct(v.top1)}</td>
                <td className="py-1.5 pr-3">{fmt.pct(v.top3)}</td>
                <td className="py-1.5">{v.n}</td>
              </tr>))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
