"use client";
import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { KIND_COLOR, STATUS_COLOR, fmt } from "@/lib/api";

type Node = { id: string; name: string; kind: string; tier: number; owner: string;
  slo_p95_ms: number; slo_error_pct: number; capacity_rps: number };
type Edge = { source: string; target: string; fanout: number };

export function ServiceGraph({ nodes, edges, health, rootCause, path, onSelect }:
  { nodes: Node[]; edges: Edge[]; health?: Record<string, any>;
    rootCause?: string | null; path?: string[][]; onSelect?: (id: string) => void }) {
  const [hover, setHover] = useState<string | null>(null);
  const W = 900, H = 420;

  // deterministic tier-based layout: columns = tier, rows spread within tier
  const pos = useMemo(() => {
    const byTier = new Map<number, Node[]>();
    nodes.forEach((n) => byTier.set(n.tier, [...(byTier.get(n.tier) ?? []), n]));
    const tiers = [...byTier.keys()].sort();
    const p: Record<string, { x: number; y: number }> = {};
    tiers.forEach((t, ti) => {
      const col = byTier.get(t)!;
      col.forEach((n, i) => {
        p[n.id] = {
          x: 90 + (ti * (W - 180)) / Math.max(1, tiers.length - 1),
          y: (H / (col.length + 1)) * (i + 1),
        };
      });
    });
    return p;
  }, [nodes]);

  const onPath = new Set((path ?? []).flat());
  const pathEdge = new Set((path ?? []).map(([a, b]) => `${a}->${b}`));

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <defs>
          <marker id="arw" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 z" fill="#2a3646" />
          </marker>
        </defs>
        {edges.map((e) => {
          const a = pos[e.source], b = pos[e.target];
          if (!a || !b) return null;
          const key = `${e.target}->${e.source}`;   // propagation flows callee->caller
          const active = pathEdge.has(key);
          const dim = hover && hover !== e.source && hover !== e.target;
          const mx = (a.x + b.x) / 2;
          return (
            <path key={`${e.source}-${e.target}`}
              d={`M${a.x},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`}
              fill="none" markerEnd="url(#arw)"
              stroke={active ? "#ff5d73" : "#22303f"}
              strokeWidth={active ? 2 : Math.min(2.4, 0.7 + e.fanout * 0.5)}
              className={active ? "flow" : undefined}
              opacity={dim ? 0.16 : active ? 0.95 : 0.5} />
          );
        })}
        {nodes.map((n) => {
          const h = health?.[n.id];
          const status = h?.status ?? "healthy";
          const c = STATUS_COLOR[status];
          const isRoot = rootCause === n.id;
          const dim = hover && hover !== n.id;
          const p = pos[n.id];
          if (!p) return null;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}
              onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
              onClick={() => onSelect?.(n.id)} style={{ cursor: "pointer" }}
              opacity={dim ? 0.34 : 1}>
              {(isRoot || status === "critical") && (
                <motion.circle r={26} fill="none" stroke={c} strokeWidth="1"
                  animate={{ r: [22, 34], opacity: [0.55, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }} />
              )}
              <circle r={isRoot ? 17 : 13} fill="#0c1219" stroke={c}
                strokeWidth={isRoot ? 2.4 : 1.5}
                style={{ filter: `drop-shadow(0 0 ${isRoot ? 12 : 5}px ${c}66)` }} />
              <circle r={4.5} fill={KIND_COLOR[n.kind] ?? "#7b8aa0"} />
              {onPath.has(n.id) && !isRoot && (
                <circle r={20} fill="none" stroke="#ff5d73" strokeWidth="0.8"
                  strokeDasharray="3 4" opacity="0.7" />
              )}
              <text y={isRoot ? 34 : 29} textAnchor="middle" fontSize="10.5"
                fill={isRoot ? "#fff" : "#9fb0c4"} fontWeight={isRoot ? 600 : 400}>
                {n.name.replace(" (external)", "")}
              </text>
              {h && (
                <text y={isRoot ? 47 : 42} textAnchor="middle" fontSize="9"
                  fill="#5d6b7d" className="metric">
                  p95 {fmt.n(h.latency_p95, 0)}ms · {fmt.n(h.error_rate, 2)}%
                </text>
              )}
              {isRoot && (
                <text y={-26} textAnchor="middle" fontSize="9" fill="#ff5d73"
                  className="metric" letterSpacing="1.2">ROOT CAUSE</text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex flex-wrap gap-3 px-1">
        {Object.entries(KIND_COLOR).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5 text-[10px] text-[--color-mute]">
            <span className="h-2 w-2 rounded-full" style={{ background: c }} />{k}
          </span>
        ))}
        <span className="ml-auto text-[10px] text-[--color-mute]">
          Red edges trace the measured propagation path outward from the root cause.
        </span>
      </div>
    </div>
  );
}
