"use client";
import { motion } from "framer-motion";
import { ReactNode } from "react";
import { STATUS_COLOR, fmt } from "@/lib/api";

export function Panel({ title, kicker, right, children, className = "" }:
  { title?: string; kicker?: string; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={`panel relative z-10 ${className}`}>
      {(title || kicker) && (
        <header className="panel-hd">
          <div>
            {kicker && <div className="kicker">{kicker}</div>}
            {title && <h3 className="text-[13px] font-medium tracking-tight">{title}</h3>}
          </div>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </motion.section>
  );
}

const PROV: Record<string, [string, string]> = {
  REAL: ["#64e08a", "Genuine computation"],
  SIMULATED: ["#ffb642", "Synthetic environment"],
  GAP: ["#7b8aa0", "Production gap"],
};
export function Provenance({ kind, note }: { kind: keyof typeof PROV; note?: string }) {
  const [c, label] = PROV[kind] ?? PROV.REAL;
  return (
    <span className="chip" style={{ color: c, borderColor: `${c}33` }} title={note ?? label}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />
      {kind}
    </span>
  );
}

export function Stat({ label, value, unit, hint, tone = "#e8eef7" }:
  { label: string; value: string | number; unit?: string; hint?: string; tone?: string }) {
  return (
    <div>
      <div className="kicker">{label}</div>
      <div className="metric mt-1 text-[26px] leading-none tracking-tight" style={{ color: tone }}>
        {value}<span className="ml-1 text-[11px] text-[--color-dim]">{unit}</span>
      </div>
      {hint && <div className="mt-1.5 text-[11px] text-[--color-mute]">{hint}</div>}
    </div>
  );
}

/** Dependency-free SVG sparkline with optional threshold band. */
export function Spark({ data, color = "#35e0d0", h = 44, threshold, fill = true }:
  { data: number[]; color?: string; h?: number; threshold?: number; fill?: boolean }) {
  if (!data?.length) return <div className="skeleton rounded" style={{ height: h }} />;
  const w = 240, lo = Math.min(...data, threshold ?? Infinity),
    hi = Math.max(...data, threshold ?? -Infinity), span = hi - lo || 1;
  const y = (v: number) => h - ((v - lo) / span) * (h - 6) - 3;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${y(v)}`);
  const id = `g${color.slice(1)}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }} preserveAspectRatio="none">
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity="0.30" />
        <stop offset="100%" stopColor={color} stopOpacity="0" />
      </linearGradient></defs>
      {fill && <polygon fill={`url(#${id})`} points={`0,${h} ${pts.join(" ")} ${w},${h}`} />}
      <polyline fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round"
        strokeLinecap="round" points={pts.join(" ")} />
      {threshold != null && (
        <line x1="0" x2={w} y1={y(threshold)} y2={y(threshold)} stroke="#ff5d73"
          strokeWidth="1" strokeDasharray="4 4" opacity="0.75" />
      )}
      <circle cx={w} cy={y(data[data.length - 1])} r="2.4" fill={color} />
    </svg>
  );
}

export function Gauge({ score }: { score: number }) {
  const status = score > 92 ? "healthy" : score > 70 ? "degraded" : "critical";
  const c = STATUS_COLOR[status], R = 52, C = 2 * Math.PI * R;
  return (
    <div className="relative grid place-items-center">
      <svg width="132" height="132" className="-rotate-90">
        <circle cx="66" cy="66" r={R} fill="none" stroke="#1b2534" strokeWidth="7" />
        <motion.circle cx="66" cy="66" r={R} fill="none" stroke={c} strokeWidth="7"
          strokeLinecap="round" strokeDasharray={C}
          animate={{ strokeDashoffset: C * (1 - Math.max(0, score) / 100) }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 9px ${c}55)` }} />
      </svg>
      <div className="absolute text-center">
        <div className="metric text-3xl tracking-tight" style={{ color: c }}>{fmt.n(score)}</div>
        <div className="kicker mt-0.5">{status}</div>
      </div>
    </div>
  );
}

export function Empty({ title, body, action }:
  { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="grid place-items-center rounded-xl border border-dashed border-[--color-line] px-6 py-14 text-center">
      <div className="max-w-md">
        <div className="mx-auto mb-3 h-8 w-8 rounded-lg border border-[--color-line] bg-[--color-panel-2]" />
        <h4 className="text-sm font-medium">{title}</h4>
        <p className="mt-1.5 text-[12px] leading-relaxed text-[--color-mute]">{body}</p>
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-[#ff5d7333] bg-[#ff5d730d] p-4">
      <div className="text-[12px] font-medium text-[--color-rose]">Backend unreachable</div>
      <p className="mt-1 text-[11px] text-[--color-mute]">
        {error} — is the API running on :8000? Start it with <code className="metric">make api</code>.
      </p>
      {onRetry && (
        <button onClick={onRetry}
          className="mt-3 rounded-md border border-[--color-line] px-2.5 py-1 text-[11px] hover:bg-white/5">
          Retry
        </button>
      )}
    </div>
  );
}

export function Btn({ children, onClick, variant = "primary", disabled, className = "" }:
  { children: ReactNode; onClick?: () => void; variant?: "primary" | "ghost" | "danger";
    disabled?: boolean; className?: string }) {
  const v = {
    primary: "bg-gradient-to-b from-[#3ddccb] to-[#22b6c9] text-[#04121a] font-semibold hover:brightness-110",
    ghost: "border border-[--color-line] text-[--color-ink] hover:bg-white/5",
    danger: "border border-[#ff5d7344] text-[--color-rose] hover:bg-[#ff5d730f]",
  }[variant];
  return (
    <button onClick={onClick} disabled={disabled}
      className={`rounded-lg px-3.5 py-2 text-[12px] tracking-tight transition-all
        disabled:cursor-not-allowed disabled:opacity-45 ${v} ${className}`}>
      {children}
    </button>
  );
}
