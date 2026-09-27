"use client";

// Shared console primitives. Every control here performs a real runtime operation:
// there are no buttons that only change local state.

import { useState, type ReactNode } from "react";
import { API, dig, post } from "@/lib/runtime";

export function Panel({
  title,
  right,
  children,
  tone = "plain",
  className = "",
}: {
  title: string;
  right?: ReactNode;
  children: ReactNode;
  tone?: "plain" | "alert" | "quiet";
  className?: string;
}) {
  const border =
    tone === "alert" ? "border-ember/40" : tone === "quiet" ? "border-gridline/70" : "border-gridline";
  return (
    <section className={`rounded-window border ${border} bg-white ${className}`}>
      <header className="flex items-center justify-between gap-3 border-b border-gridline px-3 py-2">
        <h2 className="font-mono text-caption uppercase tracking-[0.14em] text-graphite">
          {title}
        </h2>
        {right ? <div className="flex items-center gap-2">{right}</div> : null}
      </header>
      <div className="px-3 py-3">{children}</div>
    </section>
  );
}

export function Field({
  label,
  value,
  mono = false,
  tone = "plain",
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
  tone?: "plain" | "warn" | "ok";
}) {
  const c = tone === "warn" ? "text-ember-text" : tone === "ok" ? "text-ink" : "text-ink";
  return (
    <div className="min-w-0">
      <div className="font-mono text-caption uppercase tracking-[0.14em] text-slate">{label}</div>
      <div className={`truncate ${c} ${mono ? "font-mono text-[12.5px]" : "text-body"}`}>
        {value}
      </div>
    </div>
  );
}

export function Verdict({ v }: { v?: string | null }) {
  if (!v) return <span className="font-mono text-[12px] text-slate">&mdash;</span>;
  const refused = v.includes("REFUSED");
  return (
    <span
      className={`inline-block rounded-pill border px-2 py-[2px] font-mono text-[11px] uppercase tracking-[0.1em] ${
        refused ? "border-ember/50 bg-ember-glow/60 text-ember-text" : "border-gridline bg-vellum text-graphite"
      }`}
    >
      {refused ? "refused" : v.includes("ADMITTED") ? "allowed" : v.toLowerCase()}
    </span>
  );
}

export function Digest({ h, label }: { h?: string | null; label?: string }) {
  const [copied, setCopied] = useState(false);
  if (!h) return <span className="font-mono text-[12.5px] text-slate">&mdash;</span>;
  return (
    <button
      type="button"
      title={h}
      onClick={() => {
        navigator.clipboard?.writeText(h);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="group inline-flex items-baseline gap-1 font-mono text-[12.5px] text-ink hover:text-ember-text"
    >
      {label ? <span className="text-slate">{label}</span> : null}
      <span title={h}>{dig(h, 12)}</span>
      {h.length > 12 ? <span className="text-mist">...{h.slice(-6)}</span> : null}
      <span className="text-[10px] text-ember-text opacity-0 transition-opacity group-hover:opacity-100">
        {copied ? "copied" : "copy"}
      </span>
    </button>
  );
}

export function StatusPill({ status }: { status?: string | null }) {
  const s = (status || "").toUpperCase();
  const map: Record<string, string> = {
    CURRENT: "border-gridline bg-vellum text-graphite",
    STALE: "border-ember/50 bg-ember-glow/60 text-ember-text",
    DELETED: "border-ember/50 bg-white text-ember-text",
  };
  return (
    <span
      className={`inline-block rounded-pill border px-2 py-[2px] font-mono text-[11px] uppercase tracking-[0.1em] ${
        map[s] || "border-gridline bg-white text-slate"
      }`}
    >
      {(s || "unknown").toLowerCase()}
    </span>
  );
}

type RunResult = { ok?: boolean; [k: string]: unknown } | { error: string } | null;

export function Action({
  label,
  path,
  body,
  onDone,
  variant = "plain",
  confirm,
  disabled,
  title,
}: {
  label: string;
  path: string;
  body?: unknown;
  onDone?: (r: RunResult) => void;
  variant?: "plain" | "primary" | "danger";
  confirm?: string;
  disabled?: boolean;
  title?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const cls =
    variant === "primary"
      ? "border-ember bg-ember text-white hover:brightness-95"
      : variant === "danger"
      ? "border-ember/50 bg-white text-ember-text hover:bg-ember-glow/40"
      : "border-gridline bg-white text-ink hover:bg-vellum";
  return (
    <button
      type="button"
      title={title}
      disabled={busy || disabled}
      onClick={async () => {
        if (confirm && !window.confirm(confirm)) return;
        setBusy(true);
        setNote(null);
        try {
          const r = await post(path, body ?? {});
          setNote("done");
          onDone?.(r as RunResult);
        } catch (e) {
          setNote(e instanceof Error ? e.message : "failed");
          onDone?.({ error: e instanceof Error ? e.message : "failed" });
        } finally {
          setBusy(false);
        }
      }}
      className={`rounded-pill border px-3 py-[5px] font-mono text-[11.5px] uppercase tracking-[0.08em] transition-colors disabled:opacity-50 ${cls}`}
    >
      {busy ? "working" : label}
      {note ? <span className="ml-2 normal-case tracking-normal text-slate">{note}</span> : null}
    </button>
  );
}

export function RuntimeBanner({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="rounded-window border border-ember/40 bg-ember-glow/30 px-3 py-2 text-[13px] text-ember-text">
      <span className="font-mono text-[11.5px] uppercase tracking-[0.12em]">disconnected</span>
      <span className="ml-2">{error}</span>
      <div className="mt-1 font-mono text-[11.5px] text-graphite">
        start it with:{" "}
        <code className="rounded bg-white px-1 py-[1px] border border-gridline">
          python3 runtime/countersign_runtime.py
        </code>{" "}
        (expected at {API})
      </div>
    </div>
  );
}

export function JsonBlock({ value, max = 22 }: { value: unknown; max?: number }) {
  const [open, setOpen] = useState(false);
  const text = JSON.stringify(value, null, 2);
  const lines = text.split("\n");
  const shown = open ? text : lines.slice(0, max).join("\n");
  return (
    <div className="rounded-window border border-gridline bg-vellum">
      <pre className="max-h-[420px] overflow-auto px-3 py-2 font-mono text-[11.5px] leading-[1.55] text-ink">
        {shown}
        {!open && lines.length > max ? "\n\u2026" : ""}
      </pre>
      {lines.length > max ? (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="w-full border-t border-gridline px-3 py-1 font-mono text-[11px] uppercase tracking-[0.1em] text-graphite hover:bg-white"
        >
          {open ? "collapse" : `expand ${lines.length} lines`}
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-window border border-dashed border-gridline px-3 py-6 text-center text-[13px] text-slate">
      {children}
    </div>
  );
}
