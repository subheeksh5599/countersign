"use client";

// RECEIPTS: the persisted record. Each row is a real file in the repository's store.

import { useEffect, useState } from "react";
import { Action, Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, Verdict } from "@/components/console";
import { API, useApi, dateTime, ms } from "@/lib/runtime";
import { ReplayPanel } from "@/components/ops";

type ReceiptRow = {
  receipt_id: string; receipt_hash: string; timestamp: string; session_id: string;
  tool_name: string; tool_classification?: string; verdict: string; reason_code: string;
  exit_code: number; runtime_latency_ms: number | null; affected_paths: string[];
  previous_receipt_hash: string | null; seq: number;
};

export default function ReceiptsPage() {
  const [open, setOpen] = useState<string | null>(null);
  const [verify, setVerify] = useState<unknown>(null);
  const idx = useApi<{ rows: ReceiptRow[]; count: number; chain: { valid?: boolean; count?: number; reason?: string; head?: string | null } }>("/api/receipts");

  // a link from the interceptor or protect page can open one receipt directly
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("open");
    if (id) setOpen(id);
  }, []);

  const detail = useApi<Record<string, unknown> | null>(open ? `/api/receipts/${open}` : null, [open]);

  const rows = idx.data?.rows || [];
  const chain = idx.data?.chain;
  const d = detail.data;

  return (
    <div className="space-y-3">
      <RuntimeBanner error={idx.error} />

      <Panel
        title="receipt log"
        right={
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
            {idx.data?.count ?? 0} receipts &middot; chain {chain?.valid ? "valid" : "broken"}
            {chain?.head ? ` \u00b7 head ${chain.head.slice(0, 10)}` : ""}
          </span>
        }
      >
        {rows.length === 0 ? (
          <Empty>
            No receipt exists in this repository yet. A receipt is written for every verdict,
            allowed or refused, and chains to the one before it by hash.
          </Empty>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                <th className="border-b border-gridline pb-1 pr-2 font-normal">seq</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">receipt id</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">written</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">session</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">tool</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">path</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">verdict</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">exit</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">latency</th>
                <th className="border-b border-gridline pb-1 font-normal">chained to</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.receipt_id} className={open === r.receipt_id ? "bg-vellum" : ""}>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-slate">{r.seq}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px]">
                    <button
                      type="button"
                      onClick={() => { setOpen(r.receipt_id); setVerify(null); }}
                      className="text-ember-text hover:underline"
                    >
                      {r.receipt_id}
                    </button>
                  </td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{dateTime(r.timestamp)}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{r.session_id}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px]">{r.tool_name}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px]">{(r.affected_paths || [])[0] || "\u2014"}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><Verdict v={r.verdict} /></td>
                  <td className={`border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px] ${r.exit_code === 2 ? "text-ember-text" : ""}`}>{r.exit_code}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px]">{ms(r.runtime_latency_ms)}</td>
                  <td className="border-b border-gridline/60 py-[7px]"><Digest h={r.previous_receipt_hash} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <ReplayPanel />

      {chain && rows.length > 0 ? (
        <Panel title="receipt chain">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11.5px]">
            {[...rows].reverse().map((r, i) => (
              <span key={r.receipt_id} className="flex items-center gap-2">
                {i > 0 ? <span className="text-mist">&larr;</span> : null}
                <span className={`rounded-pill border px-2 py-[3px] ${r.verdict === "REFUSED" ? "border-ember/50 bg-ember-glow/40 text-ember-text" : "border-gridline bg-white text-graphite"}`}>
                  {r.seq}: {r.verdict === "REFUSED" ? "refused" : "allowed"}
                </span>
              </span>
            ))}
          </div>
          <div className="mt-2 font-mono text-[11.5px] text-slate">
            each receipt stores the hash of the one before it: {chain.valid ? "every link verifies" : chain.reason}
          </div>
        </Panel>
      ) : null}

      {open && d ? (
        <Panel
          title={`receipt \u2014 ${String(d.receipt_id)}`}
          right={
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(JSON.stringify(d, null, 2))}
                className="rounded-pill border border-gridline bg-white px-3 py-[5px] font-mono text-[11.5px] uppercase tracking-[0.08em]"
              >
                copy json
              </button>
              <a
                href={`${API}/api/receipts/${String(d.receipt_id)}/download`}
                target="_blank"
                rel="noreferrer"
                className="rounded-pill border border-gridline bg-white px-3 py-[5px] font-mono text-[11.5px] uppercase tracking-[0.08em]"
              >
                download
              </a>
              <Action label="verify receipt" path={`/api/receipts/${String(d.receipt_id)}/verify`} onDone={(r) => setVerify(r)} variant="primary" />
              <button type="button" onClick={() => { setOpen(null); setVerify(null); }} className="rounded-pill border border-gridline bg-white px-3 py-[5px] font-mono text-[11.5px] uppercase tracking-[0.08em] text-slate">
                close
              </button>
            </div>
          }
        >
          <div className="grid gap-3 md:grid-cols-4">
            <Field label="verdict" value={<Verdict v={String(d.verdict)} />} />
            <Field label="reason code" value={<span className="font-mono text-[12px]">{String(d.reason_code)}</span>} />
            <Field label="exit code" value={<span className="font-mono text-[12.5px]">{String(d.exit_code)}</span>} />
            <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(d.runtime_latency_ms as number)}</span>} />
            <Field label="session" value={<span className="font-mono text-[11.5px]">{String(d.session_id)}</span>} />
            <Field label="tool" value={<span className="font-mono text-[12px]">{String(d.tool_name)}</span>} />
            <Field label="tool arguments hash" value={<Digest h={d.tool_arguments_hash as string} />} />
            <Field label="git head at verdict" value={<Digest h={d.git_head as string} />} />
          </div>
          {verify ? <div className="mt-3"><JsonBlock value={verify} max={10} /></div> : null}
          <div className="mt-3">
            <JsonBlock value={d} max={28} />
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
