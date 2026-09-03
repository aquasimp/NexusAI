"use client";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { StageTimeline } from "@/components/StageTimeline";
import { Btn, Empty, Panel, Provenance, Stat } from "@/components/ui";
import { api, fmt, useApi, useStream } from "@/lib/api";

export default function Investigation() {
  const { data: info } = useApi<any>("/system/info");
  const { data: list, reload } = useApi<any>("/incidents");
  const [iid, setIid] = useState<string | null>(null);
  const [stages, setStages] = useState<any[]>([]);
  const [record, setRecord] = useState<any>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!list) return;
    const target = list.active ?? list.incidents?.[0]?.id ?? null;
    if (target && target !== iid) setIid(target);
  }, [list]);                                    // eslint-disable-line

  useEffect(() => {
    if (!iid) return;
    api<any>(`/incidents/${iid}`).then((d) => {
      setStages(d.stages ?? []); setRecord(d.record ?? null);
    }).catch(() => {});
  }, [iid]);

  useStream(iid ? `/stream/incident/${iid}` : null, {
    init: (d) => setStages(d.stages ?? []),
    stage: (d) => setStages((s) => [...s.filter((x) => x.stage !== d.stage || x.status !== d.status), d]),
  });
  useStream("/stream/live", {
    incident_opened: (d) => { setIid(d.incident_id); setStages([]); setRecord(null); },
    incident_closed: () => setTimeout(reload, 900),
  });

  const byId = (k: string) => stages.find((s) => s.stage === k);
  const hyp = byId("hypotheses_generated");
  const rc = byId("root_cause_ranked");
  const cor = byId("evidence_correlated");
  const imp = byId("impact_estimated");
  const plan = byId("remediation_proposed")?.plan;
  const appr = byId("approval_requested");
  const ver = byId("recovery_verified");
  const closed = byId("incident_closed");
  const truth = record?.ground_truth;

  const decide = async (approve: boolean, action_id?: string) => {
    if (!iid) return;
    setSending(true);
    try {
      await api(`/incidents/${iid}/approve`, {
        method: "POST", body: JSON.stringify({ approve, action_id, operator: "demo-operator" }),
      });
    } finally { setSending(false); }
  };

  if (!iid) return (
    <Empty title="No incident selected"
      body="Trigger one from the Command Center — NEXUS opens an investigation automatically the moment the detector's persistence gate is satisfied."
      action={<Btn onClick={() => api("/simulate", { method: "POST", body: JSON.stringify({ scenario: "random" }) })}>
        ◆ Simulate incident</Btn>} />
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="kicker">Incident investigation</div>
          <h1 className="metric mt-1 text-[22px] font-semibold tracking-tight">{iid}</h1>
        </div>
        <div className="flex items-center gap-2">
          <select value={iid} onChange={(e) => setIid(e.target.value)}
            className="metric rounded-lg border border-[--color-line] bg-[--color-panel]
                       px-2.5 py-2 text-[11px]">
            {(list?.incidents ?? []).map((i: any) => (
              <option key={i.id} value={i.id}>{i.id} · {i.status}</option>))}
          </select>
          <span className="chip" style={{
            color: closed?.status === "done" ? "#64e08a" : closed ? "#ffb642" : "#4c8dff" }}>
            {closed?.status === "done" ? "resolved" : closed?.status ?? "in flight"}
          </span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[400px_1fr]">
        <Panel kicker="Workflow" title="Investigation stages"
          right={<Provenance kind="REAL" />}>
          <StageTimeline stages={stages} all={info?.stages ?? []} />
        </Panel>

        <div className="space-y-4">
          {rc && (
            <Panel kicker="Root cause" title={rc.root_cause.class.replace(/_/g, " ")}
              right={<Provenance kind="REAL" note={`ranker: ${rc.root_cause.ranker}`} />}>
              <div className="grid gap-4 sm:grid-cols-4">
                <Stat label="service" value={rc.root_cause.service} tone="#ff5d73" />
                <Stat label="confidence" value={fmt.pct(rc.root_cause.confidence)} />
                <Stat label="margin over #2" value={fmt.n(rc.root_cause.margin, 3)} />
                <Stat label="ranker" value={rc.root_cause.ranker} />
              </div>
              <div className="mt-4 rounded-lg border border-[--color-line-soft]
                              bg-[#0a0f16] p-3.5">
                <div className="kicker mb-1.5">Analyst narrative
                  <span className="ml-2 text-[--color-cyan]">{rc.narrative?.source}</span>
                  {rc.narrative?.agreement && (
                    <span className="ml-2" style={{ color:
                      rc.narrative.agreement === "agree" ? "#64e08a" : "#ffb642" }}>
                      cross-check: {rc.narrative.agreement}</span>)}
                </div>
                <p className="text-[12.5px] leading-relaxed">{rc.narrative?.summary}</p>
                <ol className="mt-3 space-y-1.5">
                  {(rc.narrative?.reasoning ?? []).map((r: string, i: number) => (
                    <motion.li key={i} initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}
                      className="flex gap-2 text-[11.5px] leading-relaxed text-[--color-mute]">
                      <span className="metric text-[--color-dim]">{i + 1}.</span>{r}
                    </motion.li>))}
                </ol>
              </div>
            </Panel>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {hyp && (
              <Panel kicker="Hypotheses" title={`Ranked causes · ${hyp.ranker}`}
                right={<Provenance kind="REAL" />}>
                <div className="space-y-2.5">
                  {hyp.hypotheses.slice(0, 5).map((h: any, i: number) => (
                    <div key={h.class}>
                      <div className="flex items-baseline gap-2 text-[11.5px]">
                        <span className={i === 0 ? "font-medium" : "text-[--color-mute]"}>
                          {h.class.replace(/_/g, " ")}</span>
                        <span className="metric ml-auto">{fmt.pct(h.probability)}</span>
                      </div>
                      <div className="mt-1 h-[3px] overflow-hidden rounded bg-[--color-line-soft]">
                        <motion.div initial={{ width: 0 }}
                          animate={{ width: `${h.probability * 100}%` }}
                          transition={{ duration: 0.6, delay: i * 0.06 }}
                          className="h-full rounded"
                          style={{ background: i === 0
                            ? "linear-gradient(90deg,#35e0d0,#4c8dff)" : "#2a3646" }} />
                      </div>
                      {i === 0 && (
                        <ul className="mt-2 space-y-1">
                          {h.evidence.slice(0, 4).map((e: any) => (
                            <li key={e.feature} className="metric flex gap-2 text-[10px]">
                              <span style={{ color: e.direction === "supports" ? "#64e08a" : "#ff5d73" }}>
                                {e.direction === "supports" ? "+" : "−"}</span>
                              <span className="text-[--color-mute]">{e.feature}</span>
                              <span className="ml-auto">{e.value}</span>
                              <span className="w-12 text-right text-[--color-dim]">
                                {e.contribution}</span>
                            </li>))}
                        </ul>)}
                    </div>))}
                  {hyp.cross_check && (
                    <div className="mt-1 border-t border-[--color-line-soft] pt-2
                                    text-[10.5px] text-[--color-mute]">
                      Independent rule-based cross-check:
                      <span className="metric ml-1 text-[--color-ink]">
                        {hyp.cross_check.top}</span> ({fmt.pct(hyp.cross_check.confidence)})
                    </div>)}
                </div>
              </Panel>
            )}

            {cor && (
              <Panel kicker="Retrieved evidence" title="Runbook citations"
                right={<Provenance kind="REAL" note="BM25 + TF-IDF/SVD, RRF fusion" />}>
                <div className="space-y-2">
                  {(cor.citations ?? []).map((c: any, i: number) => (
                    <div key={c.doc_id} className="rounded-lg border border-[--color-line-soft]
                                                   bg-[#0a0f16] p-2.5">
                      <div className="flex items-baseline gap-2">
                        <span className="metric text-[10px] text-[--color-dim]">[{i + 1}]</span>
                        <span className="text-[11.5px] font-medium">{c.title}</span>
                        <span className="metric ml-auto text-[10px] text-[--color-cyan]">
                          {c.score}</span>
                      </div>
                      <div className="kicker mt-1">§ {c.heading}</div>
                      <p className="mt-1.5 line-clamp-3 text-[10.5px] leading-relaxed
                                    text-[--color-mute]">{c.snippet}</p>
                    </div>))}
                </div>
              </Panel>
            )}
          </div>

          {imp && (
            <Panel kicker="Impact" title="SLO & business exposure"
              right={<Provenance kind="SIMULATED"
                note="Real computation over simulated telemetry with stated assumptions" />}>
              <div className="grid gap-4 sm:grid-cols-4">
                <Stat label="severity" value={imp.impact.severity}
                  tone={imp.impact.severity === "SEV1" ? "#ff5d73" : "#ffb642"} />
                <Stat label="revenue at risk" value={fmt.usd(imp.impact.revenue_at_risk_usd)}
                  hint={`over ${fmt.n(imp.impact.duration_min)} min`} />
                <Stat label="users affected" value={fmt.compact(imp.impact.affected_users_est)}
                  hint={`${imp.impact.assumptions.requests_per_session} req/session assumed`} />
                <Stat label="SLOs breaching" value={imp.impact.breaching_slos.length}
                  hint={imp.impact.breaching_slos.slice(0, 3).join(", ")} />
              </div>
              <table className="mt-4 w-full text-left text-[11px]">
                <thead className="kicker"><tr className="border-b border-[--color-line-soft]">
                  {["Service", "err %", "SLO", "p95", "SLO", "failed reqs", "$ at risk",
                    "budget burn"].map((h, i) => <th key={i} className="py-1.5 pr-3 font-normal">{h}</th>)}
                </tr></thead>
                <tbody className="metric">
                  {imp.impact.per_service.slice(0, 6).map((r: any) => (
                    <tr key={r.service} className="border-b border-[--color-line-soft] last:border-0">
                      <td className="py-1.5 pr-3 font-sans">{r.service}</td>
                      <td className="py-1.5 pr-3 text-[--color-rose]">{r.error_rate_pct}</td>
                      <td className="py-1.5 pr-3 text-[--color-dim]">{r.slo_error_pct}</td>
                      <td className="py-1.5 pr-3">{fmt.n(r.p95_ms, 0)}</td>
                      <td className="py-1.5 pr-3 text-[--color-dim]">{r.slo_p95_ms}</td>
                      <td className="py-1.5 pr-3">{fmt.compact(r.failed_requests)}</td>
                      <td className="py-1.5 pr-3">{fmt.usd(r.revenue_at_risk_usd)}</td>
                      <td className="py-1.5">{r.error_budget_burn_pct}%</td>
                    </tr>))}
                </tbody>
              </table>
              <p className="mt-3 text-[10.5px] leading-relaxed text-[--color-dim]">
                {imp.impact.assumptions.note}
              </p>
            </Panel>
          )}

          {plan && (
            <Panel kicker="Remediation" title={plan.recommended.label}
              right={<Provenance kind="SIMULATED" note="Plan is real; execution is simulated" />}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="metric text-[12px] text-[--color-cyan]">
                    {plan.recommended.action_id} → {plan.recommended.target}</div>
                  <p className="mt-2 text-[11.5px] leading-relaxed text-[--color-mute]">
                    {plan.recommended.expected_effect}</p>
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    <span className="chip">risk: {plan.recommended.risk}</span>
                    <span className="chip">{plan.recommended.reversible ? "reversible" : "IRREVERSIBLE"}</span>
                    <span className="chip">{plan.recommended.blast_radius}</span>
                    <span className="chip" style={{ color: "#8b7cff" }}>
                      src: {plan.recommended.source_doc}</span>
                  </div>
                </div>
                <div className="rounded-lg border border-[--color-line-soft] bg-[#0a0f16] p-3">
                  <div className="kicker mb-1.5">Policy engine</div>
                  <ul className="space-y-1 text-[10.5px] text-[--color-mute]">
                    {plan.policy.rules.map((r: string) => (
                      <li key={r} className="flex gap-1.5"><span className="text-[--color-dim]">·</span>{r}</li>))}
                  </ul>
                  <div className="mt-2 text-[11px]"
                    style={{ color: plan.recommended.approval_required ? "#ffb642" : "#64e08a" }}>
                    {plan.recommended.approval_required
                      ? "→ human approval required" : "→ auto-execution permitted"}
                  </div>
                </div>
              </div>

              {appr?.status === "waiting" && (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  className="mt-4 rounded-lg border border-[#ffb64244] bg-[#ffb6420d] p-3.5">
                  <div className="text-[12px] font-medium text-[--color-amber]">
                    Approval gate — awaiting operator decision</div>
                  <p className="mt-1 text-[11px] text-[--color-mute]">
                    Execution is blocked on an asyncio gate. Approve the recommendation,
                    approve an alternative, or reject to see the escalation path.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Btn onClick={() => decide(true)} disabled={sending}>
                      ✓ Approve {plan.recommended.action_id}</Btn>
                    {plan.alternatives.slice(0, 2).map((a: any) => (
                      <Btn key={a.action_id} variant="ghost" disabled={sending}
                        onClick={() => decide(true, a.action_id)}>{a.label}</Btn>))}
                    <Btn variant="danger" onClick={() => decide(false)} disabled={sending}>
                      Reject</Btn>
                  </div>
                </motion.div>
              )}
              {ver?.verification && (
                <div className="mt-4 rounded-lg border p-3.5" style={{
                  borderColor: ver.verification.recovered ? "#64e08a44" : "#ff5d7344",
                  background: ver.verification.recovered ? "#64e08a0d" : "#ff5d730d" }}>
                  <div className="text-[12px] font-medium"
                    style={{ color: ver.verification.recovered ? "#64e08a" : "#ff5d73" }}>
                    {ver.verification.recovered
                      ? "Recovery verified by the detector"
                      : "Recovery NOT verified — hypothesis invalidated, escalated"}
                  </div>
                  <div className="metric mt-2 grid grid-cols-4 gap-3 text-[11px]">
                    <div><div className="kicker">health before</div>{fmt.n(ver.verification.health_before)}</div>
                    <div><div className="kicker">health after</div>{fmt.n(ver.verification.health_after)}</div>
                    <div><div className="kicker">clear ticks</div>{ver.verification.clear_ticks}</div>
                    <div><div className="kicker">sim MTTR</div>{fmt.n(ver.verification.mttr_s, 0)}s</div>
                  </div>
                </div>
              )}
            </Panel>
          )}

          {truth && (
            <Panel kicker="Post-hoc audit" title="Ground truth (revealed after closure)"
              right={<Provenance kind="SIMULATED" />}>
              <div className="grid gap-4 sm:grid-cols-3 text-[11.5px]">
                {[["root service", truth.root_service, record?.root_cause?.service],
                  ["root class", truth.root_class, record?.root_cause?.class],
                  ["gold actions", truth.gold_actions.join(", "), record?.plan?.recommended?.action_id],
                ].map(([label, want, got]) => (
                  <div key={label as string}>
                    <div className="kicker">{label}</div>
                    <div className="metric mt-1">{want}</div>
                    <div className="metric mt-0.5 text-[10.5px]" style={{
                      color: String(want).includes(String(got)) ? "#64e08a" : "#ff5d73" }}>
                      predicted: {got ?? "—"}
                    </div>
                  </div>))}
              </div>
              <p className="mt-3 text-[10.5px] text-[--color-dim]">{truth.disclosure}</p>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
