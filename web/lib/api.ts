"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export const KIND_COLOR: Record<string, string> = {
  edge: "#4c8dff", app: "#35e0d0", datastore: "#8b7cff",
  cache: "#ffb642", external: "#7b8aa0",
};
export const STATUS_COLOR: Record<string, string> = {
  healthy: "#64e08a", degraded: "#ffb642", critical: "#ff5d73",
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text().catch(() => "")}`);
  return r.json() as Promise<T>;
}

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const reload = useCallback(() => {
    if (!path) return;
    setLoading(true);
    api<T>(path).then(setData).catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [path]);
  useEffect(reload, [reload, ...deps]);   // eslint-disable-line react-hooks/exhaustive-deps
  return { data, error, loading, reload };
}

/** SSE with auto-reconnect and typed event dispatch. */
export function useStream(
  path: string | null,
  handlers: Record<string, (d: any) => void>,
) {
  const hRef = useRef(handlers);
  hRef.current = handlers;
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!path) return;
    let es: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout>;
    let closed = false;
    const open = () => {
      es = new EventSource(`/api${path}`);
      es.onopen = () => setConnected(true);
      es.onerror = () => {
        setConnected(false);
        es?.close();
        if (!closed) retry = setTimeout(open, 1800);
      };
      for (const name of Object.keys(hRef.current)) {
        es.addEventListener(name, (e) => {
          try { hRef.current[name]?.(JSON.parse((e as MessageEvent).data)); }
          catch { /* ignore malformed frame */ }
        });
      }
    };
    open();
    return () => { closed = true; clearTimeout(retry); es?.close(); };
  }, [path]);
  return connected;
}

export const fmt = {
  n: (v?: number | null, d = 1) =>
    v == null || Number.isNaN(v) ? "—" : v.toFixed(d),
  ms: (v?: number | null) => (v == null ? "—" :
    v >= 1000 ? `${(v / 1000).toFixed(2)}s` : `${v.toFixed(0)}ms`),
  pct: (v?: number | null, d = 1) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`),
  usd: (v?: number | null) => (v == null ? "—" :
    `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`),
  compact: (v?: number | null) => (v == null ? "—" :
    Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 })
      .format(v)),
  ci: (c?: number[]) => (c ? `[${(c[0] * 100).toFixed(1)}, ${(c[1] * 100).toFixed(1)}]` : "—"),
};
