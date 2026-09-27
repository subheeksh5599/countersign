"use client";

// The console talks to the local Countersign runtime and to nothing else. There is no
// bundled sample data anywhere in this app: if the runtime is not reachable the pages
// say so instead of showing something plausible.

import { useCallback, useEffect, useRef, useState } from "react";

export const API =
  process.env.NEXT_PUBLIC_COUNTERSIGN_API || "http://127.0.0.1:4319";

export type ApiState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

export function useApi<T>(path: string | null, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const pathRef = useRef(path);
  pathRef.current = path;

  const load = useCallback(async () => {
    const p = pathRef.current;
    if (!p) return;
    try {
      const r = await fetch(`${API}${p}`, { cache: "no-store" });
      const j = await r.json();
      if (j && j.error) {
        setError(String(j.error));
        setData(null);
      } else {
        setError(null);
        setData(j as T);
      }
    } catch (e) {
      setError(
        `runtime not reachable at ${API} (${
          e instanceof Error ? e.message : "network error"
        })`
      );
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  // Live updates: the runtime pushes events, the page refetches. No polling timer.
  useEffect(() => {
    let closed = false;
    let es: EventSource | null = null;
    const open = () => {
      if (closed) return;
      es = new EventSource(`${API}/api/stream`);
      es.onmessage = () => load();
      es.onerror = () => {
        es?.close();
        if (!closed) setTimeout(open, 2000);
      };
    };
    open();
    return () => {
      closed = true;
      es?.close();
    };
  }, [load]);

  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}

export type RuntimeEvent = {
  at?: string;
  event?: string;
  [k: string]: unknown;
};

export function useEvents(limit = 120) {
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  useEffect(() => {
    const es = new EventSource(`${API}/api/stream`);
    es.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data);
        setEvents((prev) => [ev, ...prev].slice(0, limit));
      } catch {
        /* a keepalive comment, not an event */
      }
    };
    return () => es.close();
  }, [limit]);
  return events;
}

export async function post<T>(path: string, body: unknown = {}): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({ error: "unreadable response" }));
  if (!r.ok && (j as { error?: string }).error) throw new Error((j as { error: string }).error);
  return j as T;
}

export function dig(h?: string | null, n = 12): string {
  if (!h) return "\u2014";
  return h.slice(0, n);
}

export function stamp(iso?: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

export function dateTime(iso?: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toLocaleDateString("en-GB")} ${d.toLocaleTimeString("en-GB", {
    hour12: false,
  })}`;
}

export function ms(v?: number | null): string {
  return v === null || v === undefined ? "\u2014" : `${v} ms`;
}

export function humanAge(iso?: string | null): string {
  if (!iso) return "\u2014";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "\u2014";
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}
