"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Btn, Empty, ErrorState, Gauge, Panel, Provenance, Spark, Stat } from "@/components/ui";
import { STATUS_COLOR, api, fmt, useApi, useStream } from "@/lib/api";

const MAXPTS = 90;

export default function CommandCenter() {
  const router = useRouter();
  const { data: info } = useApi<any>("/system/info");
  const { data: init, error, reload } = useApi<any>("/state");
  const [health, setHealth] = useState<any>(null);
  const [anom, setAnom] = useState<any>(null);
  const [score, setScore] = useState<number[]>([]);
  const [rps, setRps] = useState<number[]>([]);
  const [p95, setP95] = useState<number[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [incident, setIncident] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!init) return;
    setHealth(init.health); setAnom(init.anomaly);
    setIncident(init.active_incident); setLogs(init.logs ?? []);
  }, [init]);

  const connected = useStream("/stream/live", {
    tick: (d) => {
      setHealth(d.health); setAnom(d.anomaly);
      setScore((s) => [...s, d.anomaly.system_score].slice(-MAXPTS));
      setRps((s) => [...s, d.health.services["api-gateway"].rps].slice(-MAXPTS));
      setP95((s) => [...s, d.health.services["api-gateway"].latency_p95].slice(-MAXPTS));
      if (d.logs?.length) setLogs((l) => [...l, ...d.logs].slice(-70));
    },
    incident_opened: (d) => setIncident(d.incident_id),
    incident_closed: () => setIncident(null),
  });

  useEffect(() => { logRef.current?.scrollTo({ top: 1e6, behavior: "smooth" }); }, [logs]);

  const simulate = async (scenario: string) => {
    setBusy(true);
    try {
      const r = await api<any>("/simulate", {
        method: "POST", body: JSON.stringify({ scenario }),
      });
      if (r.ok) setTimeout(() => router.push("/incident"), 1400);
    } finally { setBusy(false); }
  };

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!health) return (
    <div className="grid gap-4 lg:grid-cols-3">
      {[0, 1, 2].map((i) => <div key={i} className="skeleton h-52 rounded-xl" />)}
    </div>
  );

  const svcs = Object.entries(health.services) as [string, any][];
  const firing: string[] = anom?.firing ?? [];
  const crit = svcs.filter(([, v]) => v.status !== "healthy").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="kicker">Command center</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em]">
            Live service mesh
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="chip" style={{ color: connected ? "#64e08a" : "#ffb642" }}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "" : "pulse"}`}
              style={{ background: connected ? "#64e08a" : "#ffb642" }} />
            {connected ? "streaming" : "reconnecting"}
          </span>
          {incident ? (
            <Link href="/incident">
              <Btn variant="danger" className="pulse">Investigation live →</Btn>
            </Link>
          ) : (
            <Btn onClick={() => simulate("random")} disabled={busy}>
              {busy ? "Injecting fault…" : "◆ Simulate incident"}
            </Btn>
          )}
          <Btn variant="ghost" onClick={() => api("/reset", { method: "POST" })}>Reset</Btn>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <Panel kicker="System health" title="Weighted SLO score"
          right={<Provenance kind="REAL" />}>
          <div className="flex flex-col items-center gap-4">
            <Gauge score={health.score} />
            <div className="grid w-full grid-cols-3 gap-2 text-center">
              <div><div className="kicker">Services</div>
                <div className="metric text-sm">{svcs.length}</div></div>
              <div><div className="kicker">Degraded</div>
                <div className="metric text-sm" style={{ color: crit ? "#ffb642" : "#64e08a" }}>{crit}</div></div>
              <div><div className="kicker">Firing</div>
                <div className="metric text-sm" style={{ color: firing.length ? "#ff5d73" : "#64e08a" }}>
                  {firing.length}</div></div>
            </div>
          </div>
        </Panel>

        <div className="grid gap-4 sm:grid-cols-3">
          <Panel kicker="Anomaly signal" title="Fused score vs threshold"
            right={<Provenance kind="REAL" note="Mahalanobis + IsolationForest percentile fusion" />}>
            <Stat label="current" value={fmt.n(anom?.system_score, 4)}
              tone={anom?.system_score >= anom?.threshold ? "#ff5d73" : "#64e08a"}
              hint={`threshold ${fmt.n(anom?.threshold, 4)} · ${info?.detector?.persistence} persistence`} />
            <div className="mt-2"><Spark data={score} threshold={anom?.threshold}
              color={anom?.system_score >= anom?.threshold ? "#ff5d73" : "#35e0d0"} /></div>
          </Panel>
          <Panel kicker="Ingress" title="Gateway request rate"
            right={<Provenance kind="SIMULATED" />}>
            <Stat label="req/s" value={fmt.compact(health.services["api-gateway"].rps)}
              hint="diurnal seasonality + AR(1) noise" />
            <div className="mt-2"><Spark data={rps} color="#4c8dff" /></div>
          </Panel>
          <Panel kicker="Latency" title="Gateway p95"
            right={<Provenance kind="SIMULATED" />}>
            <Stat label="ms" value={fmt.n(health.services["api-gateway"].latency_p95, 0)}
              tone={health.services["api-gateway"].latency_p95 > 450 ? "#ffb642" : "#e8eef7"}
              hint="SLO 450ms · M/M/1 queueing delay" />
            <div className="mt-2"><Spark data={p95} color="#8b7cff" threshold={450} /></div>
          </Panel>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <Panel kicker="Services" title="Per-service state & anomaly score"
          right={<Provenance kind="REAL" note="Scores are real; telemetry is simulated" />}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11.5px]">
              <thead className="kicker">
                <tr className="border-b border-[--color-line-soft]">
                  {["Service", "State", "p95", "err %", "cpu", "mem", "util",
                    "anomaly", "top signal"].map((h) => (
                    <th key={h} className="py-2 pr-3 font-normal">{h}</th>))}
                </tr>
              </thead>
              <tbody className="metric">
                {svcs.sort((a, b) => b[1].anomaly - a[1].anomaly).map(([id, v]) => (
                  <motion.tr key={id} layout
                    className="border-b border-[--color-line-soft] last:border-0
                               hover:bg-white/[0.02]">
                    <td className="py-2 pr-3 font-sans">{id}</td>
                    <td className="py-2 pr-3">
                      <span className="chip" style={{ color: STATUS_COLOR[v.status],
                        borderColor: `${STATUS_COLOR[v.status]}33` }}>{v.status}</span>
                    </td>
                    <td className="py-2 pr-3">{fmt.n(v.latency_p95, 0)}</td>
                    <td className="py-2 pr-3" style={{ color: v.error_rate > 1 ? "#ff5d73" : undefined }}>
                      {fmt.n(v.error_rate, 2)}</td>
                    <td className="py-2 pr-3">{fmt.n(v.cpu, 0)}</td>
                    <td className="py-2 pr-3" style={{ color: v.mem > 88 ? "#ffb642" : undefined }}>
                      {fmt.n(v.mem, 0)}</td>
                    <td className="py-2 pr-3">{fmt.n(v.utilization, 2)}</td>
                    <td className="py-2 pr-3" style={{ color: v.firing ? "#ff5d73" : "#4d5a6c" }}>
                      {fmt.n(v.anomaly, 3)}{v.firing ? " ▲" : ""}</td>
                    <td className="py-2 font-sans text-[10.5px] text-[--color-mute]">
                      {(anom?.services?.[id]?.top_metrics ?? [])
                        .map((m: any) => `${m.metric} |z|=${m.abs_z}`).slice(0, 2).join(", ")}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel kicker="Scenario library" title="Inject a reproducible fault"
            right={<Provenance kind="SIMULATED" />}>
            <div className="space-y-1.5">
              {(info?.scenarios ?? []).map((s: any) => (
                <button key={s.id} onClick={() => simulate(s.id)} disabled={busy || !!incident}
                  className="group w-full rounded-lg border border-[--color-line]
                    p-2.5 text-left transition hover:border-[#35e0d055] hover:bg-white/[0.03]
                    disabled:opacity-40">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium">{s.title}</span>
                    <span className="chip ml-auto"
                      style={{ color: s.severity === "SEV1" ? "#ff5d73" : "#ffb642" }}>
                      {s.severity}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[10.5px] leading-relaxed text-[--color-mute]">
                    {s.blurb}</p>
                </button>
              ))}
            </div>
          </Panel>

          <Panel kicker="Log stream" title="Live events"
            right={<Provenance kind="SIMULATED" note="Rates driven by the metric state" />}>
            <div ref={logRef} className="metric h-56 space-y-1 overflow-y-auto pr-1 text-[10.5px]">
              {logs.length === 0
                ? <Empty title="No events yet" body="The log stream fills as the simulation ticks." />
                : logs.map((l, i) => (
                  <div key={i} className="flex gap-2 leading-relaxed">
                    <span className="text-[--color-dim]">{l.tick}</span>
                    <span style={{ color: { FATAL: "#ff5d73", ERROR: "#ff5d73",
                      WARN: "#ffb642", INFO: "#4d5a6c" }[l.level as string] }}
                      className="w-10 shrink-0">{l.level}</span>
                    <span className="w-32 shrink-0 truncate text-[--color-blue]">{l.service}</span>
                    <span className="min-w-0 flex-1 truncate text-[--color-mute]"
                      title={l.message}>{l.message}</span>
                  </div>))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
