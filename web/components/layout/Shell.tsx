"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApi } from "@/lib/api";

const NAV = [
  { href: "/command", label: "Command Center" },
  { href: "/incident", label: "Investigation" },
  { href: "/map", label: "Service Map" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/architecture", label: "Architecture" },
  { href: "/about", label: "About" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { data } = useApi<any>("/system/info");
  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-50 border-b border-[--color-line]
                         bg-[#05070ccc] backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-6 px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-6 w-6 place-items-center rounded-md
              bg-gradient-to-br from-[#35e0d0] to-[#4c8dff] text-[11px] font-bold text-[#04121a]">N</span>
            <span className="text-[13px] font-semibold tracking-[-0.01em]">NEXUS<span
              className="text-[--color-cyan]">AI</span></span>
          </Link>
          <nav className="flex items-center gap-0.5">
            {NAV.map((n) => {
              const active = path.startsWith(n.href);
              return (
                <Link key={n.href} href={n.href}
                  className={`rounded-md px-2.5 py-1.5 text-[12px] transition-colors ${
                    active ? "bg-white/[0.06] text-[--color-ink]"
                           : "text-[--color-mute] hover:text-[--color-ink]"}`}>
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-2.5">
            <span className="chip" title={data?.llm?.note}>
              <span className="h-1.5 w-1.5 rounded-full"
                style={{ background: data?.llm?.mode === "live" ? "#64e08a" : "#ffb642" }} />
              {data?.llm?.provider ?? "…"}
            </span>
            <span className="chip" title={`Root-cause ranker: ${data?.ranker?.mode}`}>
              ranker: {data?.ranker?.mode ?? "…"}
            </span>
            <span className="chip metric">t={data?.tick ?? "—"}</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-6 py-7">{children}</main>
    </div>
  );
}
