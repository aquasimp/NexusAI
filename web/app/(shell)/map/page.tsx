"use client";
import { useEffect, useState } from "react";
import { ServiceGraph } from "@/components/ServiceGraph";
import { ErrorState, Panel, Provenance, Stat } from "@/components/ui";
import { fmt, useApi, useStream } from "@/lib/api";

export default function ServiceMap() {
  const { data: topo, error, reload } = useApi<any>("/topology");
  const { data: st } = useApi<any>("/state");
  const { data: incidents } = useApi<any>("/incidents");
  const [health, setHealth] = useState<any>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [blame, setBlame] = useState<any>(null);

  useEffect(() => { if (st) setHealth(st.health.services); }, [st]);
  useStream("/stream/live", { tick: (d) => setHealth(d.health.services) });

  useEffect(() => {
    const id = incidents?.active ?? incidents?.incidents?.[0]?.id;
    if (!id) return;
    fetch(`/api/incidents/${id}`).then((r) => r.json())
      .then((d) => setBlame(d.stages?.find((s: any) => s.stage === "localize_service")?.blame))
      .catch(() => {});
  }, [incidents]);

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!topo) return <div className="skeleton h-[520px] rounded-xl" />;
  const node = topo.nodes.find((n: any) => n.id === sel);
  const h = sel ? health?.[sel] : null;

  return (
    <div className="space-y-4">
      <div>
        <div className="kicker">Service map</div>
        <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em]">
          Dependency topology & blast radius</h1>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Panel kicker="Topology" title="Live dependency graph"
          right={<Provenance kind="REAL" note="Graph & propagation path are computed" />}>
          <ServiceGraph nodes={topo.nodes} edges={topo.edges} health={health}
            rootCause={blame?.leader} path={blame?.propagation_path} onSelect={setSel} />
        </Panel>
        <div className="space-y-4">
          {blame && (
            <Panel kicker="Localization" title="Blame ranking">
              <div className="space-y-2">
                {blame.ranking.slice(0, 5).map((r: any, i: number) => (
                  <div key={r.service} className="rounded-lg border border-[--color-line-soft] p-2.5">
                    <div className="flex items-baseline gap-2 text-[11.5px]">
                      <span className="metric text-[--color-dim]">#{i + 1}</span>
                      <span className={i === 0 ? "font-medium" : "text-[--color-mute]"}>{r.service}</span>
                      <span className="metric ml-auto" style={{ color: i === 0 ? "#ff5d73" : undefined }}>
                        {r.blame}</span>
                    </div>
                    <div className="metric mt-1.5 grid grid-cols-3 gap-2 text-[9.5px] text-[--color-mute]">
                      <span>lead {r.onset_lead_s}s</span>
                      <span>up {r.upstreamness}</span>
                      <span>anom {r.anomaly_score}</span>
                    </div>
                  </div>))}
              </div>
              <p className="mt-3 text-[10.5px] leading-relaxed text-[--color-dim]">
                Blame = 0.40·magnitude + 0.24·onset lead + 0.24·upstreamness +
                0.12·deploy proximity. Upstreamness is measured on the anomalous subgraph.
              </p>
            </Panel>
          )}
          <Panel kicker="Inspector" title={node?.name ?? "Select a node"}>
            {!node ? (
              <p className="text-[11.5px] text-[--color-mute]">
                Click any node to inspect its SLOs, capacity and live state.</p>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Stat label="kind" value={node.kind} />
                  <Stat label="owner" value={node.owner} />
                  <Stat label="SLO p95" value={node.slo_p95_ms} unit="ms" />
                  <Stat label="SLO err" value={node.slo_error_pct} unit="%" />
                  <Stat label="capacity" value={fmt.compact(node.capacity_rps)} unit="rps" />
                  <Stat label="timeout" value={node.timeout_ms} unit="ms" />
                </div>
                {h && (
                  <div className="metric grid grid-cols-3 gap-2 rounded-lg border
                                  border-[--color-line-soft] bg-[#0a0f16] p-2.5 text-[11px]">
                    <div><div className="kicker">p95</div>{fmt.n(h.latency_p95, 0)}ms</div>
                    <div><div className="kicker">err</div>{fmt.n(h.error_rate, 2)}%</div>
                    <div><div className="kicker">util</div>{fmt.n(h.utilization, 2)}</div>
                  </div>)}
                <div>
                  <div className="kicker mb-1">Depends on</div>
                  <div className="flex flex-wrap gap-1.5">
                    {topo.edges.filter((e: any) => e.source === node.id)
                      .map((e: any) => <span key={e.target} className="chip">
                        {e.target} ×{e.fanout}</span>)}
                    {!topo.edges.some((e: any) => e.source === node.id) &&
                      <span className="text-[11px] text-[--color-dim]">leaf node</span>}
                  </div>
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
