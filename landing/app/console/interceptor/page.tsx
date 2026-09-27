"use client";

// INTERCEPTOR: every call the gate actually saw, with the verdict it returned.

import Link from "next/link";
import { useState } from "react";
import { Action, Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, Verdict } from "@/components/console";
import { useApi, dig, ms, stamp } from "@/lib/runtime";

type Call = {
  at: string; tool: string; classification: string; classification_reason: string; path: string | null;
  session_id: string; verdict: string; reason_code: string | null; exit_code: number;
  latency_ms: number | null; receipt_id: string | null; receipt_hash: string | null;
  held_digest: string | null; current_digest: string | null; arguments?: unknown;
  arguments_hash?: string | null;
};

const FILTERS = ["all", "allowed", "refused"] as const;

export default function InterceptorPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [replay, setReplay] = useState<unknown>(null);
  const api = useApi<{ rows: Call[] }>(`/api/interceptor?filter=${filter}`);
  const rows = api.data?.rows || [];
  const selected = rows.find((r) => r.receipt_id === open) || null;

  return (
    <div className="space-y-3">
      <RuntimeBanner error={api.error} />

      <Panel
        title="intercepted tool calls"
        right={
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
              {rows.length} shown
            </span>
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`rounded-pill border px-2 py-[3px] font-mono text-[11px] uppercase tracking-[0.1em] ${
                  filter === f ? "border-ink bg-white text-ink" : "border-gridline bg-white text-slate"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        }
      >
        {rows.length === 0 ? (
          <Empty>
            No intercepted call matches this filter. Every state-changing call the agent makes
            through the hook is listed here with its real exit code.
          </Empty>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                <th className="border-b border-gridline pb-1 pr-2 font-normal">time</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">tool</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">class</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">target</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">verdict</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">reason</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">exit</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">latency</th>
                <th className="border-b border-gridline pb-1 font-normal">receipt</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.receipt_id || r.at + r.tool} className={open === r.receipt_id ? "bg-vellum" : ""}>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{stamp(r.at)}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px]">{r.tool}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11px] text-slate">{r.classification}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px]">{r.path || "\u2014"}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><Verdict v={r.verdict} /></td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{r.reason_code || "\u2014"}</td>
                  <td className={`border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px] ${r.exit_code === 2 ? "text-ember-text" : ""}`}>{r.exit_code}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px]">{ms(r.latency_ms)}</td>
                  <td className="border-b border-gridline/60 py-[7px] font-mono text-[11.5px]">
                    {r.receipt_id ? (
                      <button type="button" onClick={() => { setOpen(open === r.receipt_id ? null : r.receipt_id); setReplay(null); }} className="text-ember-text hover:underline">
                        {dig(r.receipt_id, 14)}
                      </button>
                    ) : (
                      "\u2014"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {selected ? (
        <Panel
          title={`refused call detail \u2014 ${selected.tool} on ${selected.path || "no path"}`}
          right={
            <div className="flex gap-2">
              <Action
                label="replay check"
                path="/api/interceptor/replay"
                body={{ receipt_id: selected.receipt_id }}
                onDone={(r) => setReplay(r)}
              />
              <Link href={`/console/receipts?open=${selected.receipt_id}`} className="rounded-pill border border-gridline bg-white px-3 py-[5px] font-mono text-[11.5px] uppercase tracking-[0.08em] text-ink">
                open receipt
              </Link>
            </div>
          }
        >
          <div className="grid gap-3 md:grid-cols-4">
            <Field label="tool" value={<span className="font-mono text-[12.5px]">{selected.tool}</span>} />
            <Field label="classification" value={<span className="font-mono text-[11.5px]">{selected.classification}</span>} />
            <Field label="affected paths" value={<span className="font-mono text-[12.5px]">{selected.path || "\u2014"}</span>} />
            <Field label="verdict / exit" value={<span className="flex items-center gap-2"><Verdict v={selected.verdict} /><span className="font-mono text-[12.5px]">{selected.exit_code}</span></span>} />
            <Field label="old digest" value={<Digest h={selected.held_digest} />} tone="warn" />
            <Field label="current digest" value={<Digest h={selected.current_digest} />} />
            <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(selected.latency_ms)}</span>} />
            <Field label="arguments hash" value={<Digest h={selected.arguments_hash} />} />
          </div>

          <div className="mt-3 border-t border-gridline pt-2">
            <div className="font-mono text-caption uppercase tracking-[0.14em] text-slate">classification decision</div>
            <div className="font-mono text-[11.5px] text-graphite">{selected.classification_reason}</div>
          </div>

          <div className="mt-3 border-t border-gridline pt-2">
            <div className="mb-1 font-mono text-caption uppercase tracking-[0.14em] text-slate">
              tool arguments as the gate received them (secrets redacted, structure preserved)
            </div>
            <JsonBlock value={selected.arguments ?? {}} max={16} />
          </div>

          {replay ? (
            <div className="mt-3 border-t border-gridline pt-2">
              <div className="mb-1 font-mono text-caption uppercase tracking-[0.14em] text-slate">
                replay: the same deterministic check, run against the repository right now
              </div>
              <JsonBlock value={replay} max={20} />
            </div>
          ) : null}
        </Panel>
      ) : null}
    </div>
  );
}
