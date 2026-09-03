"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Provenance } from "../ui/ui";

const ICONS: Record<string, string> = {
  done: "✓", running: "◐", waiting: "⏸", failed: "✕", approved: "✓",
  rejected: "✕", auto_approved: "⚡", timeout: "⏱", escalated: "↑",
};
const TONE: Record<string, string> = {
  done: "#64e08a", approved: "#64e08a", auto_approved: "#35e0d0",
  running: "#4c8dff", waiting: "#ffb642", failed: "#ff5d73",
  rejected: "#ff5d73", timeout: "#ff5d73", escalated: "#ffb642",
};

export function StageTimeline({ stages, all }:
  { stages: any[]; all: { id: string; label: string }[] }) {
  const byId = new Map(stages.map((s) => [s.stage, s]));
  return (
    <ol className="relative space-y-0">
      <div className="absolute left-[11px] top-2 bottom-2 w-px bg-[--color-line-soft]" />
      {all.map((def, i) => {
        const ev = byId.get(def.id);
        const tone = ev ? TONE[ev.status] ?? "#7b8aa0" : "#2a3444";
        return (
          <li key={def.id} className="relative flex gap-3 py-2 pl-0">
            <motion.span initial={false}
              animate={{ scale: ev?.status === "running" || ev?.status === "waiting" ? [1, 1.14, 1] : 1 }}
              transition={{ duration: 1.4, repeat: ev ? Infinity : 0 }}
              className="relative z-10 mt-0.5 grid h-[23px] w-[23px] shrink-0 place-items-center
                         rounded-full border text-[10px]"
              style={{ borderColor: tone, color: tone,
                background: "#0a0f16",
                boxShadow: ev ? `0 0 10px ${tone}44` : "none" }}>
              {ev ? ICONS[ev.status] ?? "•" : i + 1}
            </motion.span>
            <div className="min-w-0 flex-1 pb-1">
              <div className="flex items-baseline gap-2">
                <span className="text-[12.5px] font-medium tracking-tight"
                  style={{ color: ev ? "#e8eef7" : "#465364" }}>{def.label}</span>
                {ev && <span className="metric text-[10px] text-[--color-dim]">
                  +{(ev.elapsed_ms / 1000).toFixed(2)}s</span>}
                {ev?.provenance && (
                  <Provenance kind={ev.provenance.startsWith("REAL") ? "REAL" : "SIMULATED"}
                    note={ev.provenance} />
                )}
              </div>
              <AnimatePresence>
                {ev?.detail && (
                  <motion.p initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-1 text-[11.5px] leading-relaxed text-[--color-mute]">
                    {ev.detail}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
