import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NEXUS AI — Autonomous Incident Intelligence",
  description:
    "Detects anomalies in live service telemetry, investigates with an agentic workflow, ranks root cause with evidence, and recommends a policy-gated remediation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body>{children}</body></html>
  );
}
