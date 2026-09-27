"use client";

// SELF-TEST: the whole product, run against a fresh temporary repository, with the real
// exit codes the gate produced. Nothing here is pre-recorded.

import { useState } from "react";
import { Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, Verdict } from "@/components/console";
import { post, stamp, ms } from "@/lib/runtime";

type Step = {
  step: string; detail: string; at: string; ok?: boolean; exit_code?: number; wall_ms?: number;
  stdout?: string; held?: string; current?: string; output?: string[];
};
type Receipt = {
  receipt_id: string; receipt_hash: string; verdict: string; reason_code: string;
  timestamp: string;
  exit_code: number; runtime_latency_ms: number | null; previous_receipt_hash: string | null;
  tool_name: string; affected_paths: string[]; tool_arguments?: unknown;
};
type Run = { verdict: string; exit_code: number; receipt: Receipt | null };
type Result = {
  ok?: boolean; label?: string; session_id?: string; repository?: string;
  held_digest?: string; digest_after_external_change?: string; digest_after_allowed_edit?: string;
  run_1?: Run; run_2?: Run; receipts?: Receipt[]; steps?: Step[]; file_after?: string;
  hook_install?: { ok?: boolean; output?: string[] };
  error?: string;
};

export default function SelfTestPage() {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Result | null>(null);

  const run = async (path: string) => {
    setBusy(true);
    setRes(null);
    try {
      setRes(await post<Result>(path, {}));
    } catch (e) {
      setRes({ error: e instanceof Error ? e.message : "failed" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      {res?.error ? <RuntimeBanner error={res.error} /> : null}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-window border border-gridline bg-white px-4 py-3">
        <div>
          <div className="text-heading-sm">countersign self-test</div>
          <div className="text-[13px] text-slate">
            Creates a real git repository, writes a config file, reads it through the gate, changes
            it from a second process, attempts the edit, refreshes the evidence, retries. Both
            attempts write receipts.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => run("/api/selftest")}
            disabled={busy}
            className="rounded-pill border border-ember bg-ember px-4 py-[7px] font-mono text-[12px] uppercase tracking-[0.08em] text-white disabled:opacity-60"
          >
            {busy ? "running" : "run countersign self-test"}
          </button>
          <button
            type="button"
            onClick={() => run("/api/demo/start")}
            disabled={busy}
            className="rounded-pill border border-gridline bg-white px-4 py-[7px] font-mono text-[12px] uppercase tracking-[0.08em] text-ink disabled:opacity-60"
          >
            start demo
          </button>
        </div>
      </div>

      {!res && !busy ? (
        <Empty>
          Nothing has been run in this browser session yet. The button above drives the real gate as
          a subprocess on a fresh repository and reports the exit codes it returned.
        </Empty>
      ) : null}

      {busy ? (
        <Panel title="running">
          <div className="font-mono text-[12px] text-graphite">
            building the repository, recording evidence, changing the file, intercepting the call...
          </div>
        </Panel>
      ) : null}

      {res && !res.error ? (
        <>
          <div className="grid gap-3 md:grid-cols-2">
            <Panel title={"run 1 \u00b7 the stale attempt"} tone="alert">
              <div className="grid grid-cols-2 gap-3">
                <Field label="verdict" value={<Verdict v={res.run_1?.verdict} />} />
                <Field label="exit code" value={<span className="font-mono text-[12.5px] text-ember-text">{res.run_1?.exit_code}</span>} />
                <Field label="reason" value={<span className="font-mono text-[12px]">{res.run_1?.receipt?.reason_code || "\u2014"}</span>} />
                <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(res.run_1?.receipt?.runtime_latency_ms)}</span>} />
                <Field label="held digest" value={<Digest h={res.held_digest} />} tone="warn" />
                <Field label="digest on disk" value={<Digest h={res.digest_after_external_change} />} />
              </div>
              <div className="mt-2 border-t border-gridline pt-2 font-mono text-[11.5px] text-graphite">
                {res.run_1?.receipt?.receipt_id} &middot; chained to{" "}
                {res.run_1?.receipt?.previous_receipt_hash ? res.run_1.receipt.previous_receipt_hash.slice(0, 12) : "nothing (first receipt in this repository)"}
              </div>
            </Panel>

            <Panel title={"run 2 \u00b7 the same call after refresh"}>
              <div className="grid grid-cols-2 gap-3">
                <Field label="verdict" value={<Verdict v={res.run_2?.verdict} />} />
                <Field label="exit code" value={<span className="font-mono text-[12.5px]">{res.run_2?.exit_code}</span>} />
                <Field label="reason" value={<span className="font-mono text-[12px]">{res.run_2?.receipt?.reason_code || "none"}</span>} />
                <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(res.run_2?.receipt?.runtime_latency_ms)}</span>} />
                <Field label="held after refresh" value={<Digest h={res.digest_after_external_change} />} />
                <Field label="digest after the allowed edit" value={<Digest h={res.digest_after_allowed_edit} />} />
              </div>
              <div className="mt-2 border-t border-gridline pt-2 font-mono text-[11.5px] text-graphite">
                {res.run_2?.receipt?.receipt_id} &middot; chained to{" "}
                {res.run_2?.receipt?.previous_receipt_hash?.slice(0, 12) || "\u2014"}
              </div>
            </Panel>
          </div>

          <Panel
            title="steps as they ran"
            right={
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                repository {res.repository?.split("/").slice(-1)[0]} &middot; session {res.session_id}
              </span>
            }
          >
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                  <th className="border-b border-gridline pb-1 pr-2 font-normal">#</th>
                  <th className="border-b border-gridline pb-1 pr-2 font-normal">step</th>
                  <th className="border-b border-gridline pb-1 pr-2 font-normal">what happened</th>
                  <th className="border-b border-gridline pb-1 pr-2 font-normal">exit</th>
                  <th className="border-b border-gridline pb-1 pr-2 font-normal">wall</th>
                  <th className="border-b border-gridline pb-1 font-normal">ok</th>
                </tr>
              </thead>
              <tbody>
                {(res.steps || []).map((s, i) => (
                  <tr key={i}>
                    <td className="border-b border-gridline/60 py-[6px] pr-2 font-mono text-[11.5px] text-slate">{i + 1}</td>
                    <td className="border-b border-gridline/60 py-[6px] pr-2 text-[12.5px]">{s.step}</td>
                    <td className="border-b border-gridline/60 py-[6px] pr-2 font-mono text-[11px] text-graphite">{s.detail}</td>
                    <td className={`border-b border-gridline/60 py-[6px] pr-2 font-mono text-[12px] ${s.exit_code === 2 ? "text-ember-text" : ""}`}>
                      {s.exit_code ?? "\u2014"}
                    </td>
                    <td className="border-b border-gridline/60 py-[6px] pr-2 font-mono text-[11.5px]">{s.wall_ms ? `${s.wall_ms} ms` : "\u2014"}</td>
                    <td className="border-b border-gridline/60 py-[6px] font-mono text-[11.5px]">{s.ok ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {res.file_after ? (
              <div className="mt-3 border-t border-gridline pt-2">
                <div className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                  src/config.ts on disk after the run
                </div>
                <pre className="mt-1 rounded-window border border-gridline bg-vellum px-3 py-2 font-mono text-[12px]">
                  {res.file_after}
                </pre>
              </div>
            ) : null}
          </Panel>

          {res.receipts && res.receipts.length > 0 ? (
            <Panel title="receipts written by this run">
              {res.receipts.map((r) => (
                <div key={r.receipt_id} className="border-b border-gridline/60 py-2 last:border-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-[11.5px] text-ink">{r.receipt_id}</span>
                    <Verdict v={r.verdict} />
                    <span className={`font-mono text-[11.5px] ${r.exit_code === 2 ? "text-ember-text" : "text-slate"}`}>
                      exit {r.exit_code}
                    </span>
                    <span className="font-mono text-[11.5px] text-slate">{r.reason_code}</span>
                    <span className="font-mono text-[11.5px] text-slate">{stamp(r.timestamp)}</span>
                  </div>
                  <div className="mt-1">
                    <JsonBlock value={r} max={16} />
                  </div>
                </div>
              ))}
            </Panel>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
