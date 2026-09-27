"use client";

// PROTECT: the operational homepage. Everything is read from the runtime, and every
// control performs a real operation on a real repository. Labels and controls only:
// no paragraph explains what a button does.

import Link from "next/link";
import { useState } from "react";
import { Action, Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, StatusPill, Verdict } from "@/components/console";
import { useApi, useEvents, dig, humanAge, ms, stamp } from "@/lib/runtime";
import { AgentTurn, StalePanel } from "@/components/ops";

type Counts = { total: number; stale: number; current: number; deleted: number };
type Status = {
  protected?: boolean; repository?: string | null; branch?: string | null; head?: string | null;
  session_id?: string | null; hook_installed?: boolean;
  hook_scope?: { installed?: boolean; scope?: string | null; files?: string[] };
  last_verdict?: string | null; last_receipt_id?: string | null; last_receipt_hash?: string | null;
  last_latency_ms?: number | null; receipt_count?: number; stale?: number;
  chain?: { valid?: boolean; count?: number; head?: string | null; reason?: string };
  evidence?: Counts; runtime?: { version?: string; port?: number; uptime_s?: number };
  disconnected?: boolean; detail?: string;
};
type EvRow = {
  path: string; type: string; held_digest: string | null; current_digest: string | null;
  git_revision: string | null; read_at: string | null; verified_at: string | null;
  via: string; status: string;
};
type Call = {
  at: string; tool: string; classification: string; classification_reason: string; path: string | null;
  verdict: string; reason_code: string | null; exit_code: number; latency_ms: number | null;
  receipt_id: string | null; receipt_hash: string | null; held_digest: string | null;
  current_digest: string | null; arguments?: unknown;
};
type Receipt = {
  receipt_id: string; receipt_hash: string; timestamp: string; session_id: string; tool_name: string;
  verdict: string; reason_code: string; exit_code: number; runtime_latency_ms: number | null;
  affected_paths: string[]; previous_receipt_hash: string | null;
};
type Repo = {
  repository?: string | null; branch?: string | null; head?: string | null;
  head_short?: string; working_tree?: { clean?: boolean; changed?: string[] };
  protected_files?: string[]; commits?: string; remote?: string | null;
  settings?: string[]; protected?: boolean;
};
type Security = {
  hook_installed?: boolean; hook_scope?: string | null; runtime_connected?: boolean;
  repository_protected?: boolean; session_valid?: boolean; hook_files?: string[];
  receipt_chain?: { valid?: boolean; count?: number; reason?: string };
  verdict_path?: string;
};

export default function ProtectPage() {
  const status = useApi<Status>("/api/status");
  const evidence = useApi<{ rows: EvRow[]; counts: Counts; session_id: string | null }>("/api/evidence");
  const interceptor = useApi<{ rows: Call[] }>("/api/interceptor");
  const receipts = useApi<{ rows: Receipt[]; count: number }>("/api/receipts");
  const security = useApi<Security>("/api/security");
  const repo = useApi<Repo>("/api/repo");
  const [connectPath, setConnectPath] = useState("");
  const [opPath, setOpPath] = useState("src/config.ts");
  const events = useEvents(10);

  const s = status.data || {};
  const rows = evidence.data?.rows || [];
  const calls = interceptor.data?.rows || [];
  const last = calls[0];
  const lastReceipt = receipts.data?.rows?.[0];
  const staleRows = rows.filter((r) => r.status === "STALE");
  const watch = rows.filter((r) => r.type === "file_read").slice(0, 6);
  const sec = security.data;

  const refreshAll = () => {
    status.reload();
    evidence.reload();
    interceptor.reload();
    receipts.reload();
    security.reload();
    repo.reload();
  };

  return (
    <div className="space-y-3">
      <RuntimeBanner error={status.error} />

      {/* status strip */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-window border border-gridline bg-white px-3 py-2">
        <Field
          label="countersign"
          value={
            s.disconnected ? (
              <span className="font-mono text-[12.5px] text-ember-text">OFFLINE</span>
            ) : s.protected ? (
              <span className="font-mono text-[12.5px] text-ink">PROTECTED</span>
            ) : (
              <span className="font-mono text-[12.5px] text-ember-text">HOOK OFF</span>
            )
          }
        />
        <Field label="repository" value={<span className="font-mono text-[12px]">{s.repository ? s.repository.split("/").slice(-2).join("/") : "\u2014"}</span>} />
        <Field label="branch" value={<span className="font-mono text-[12.5px]">{s.branch || "\u2014"}</span>} />
        <Field label="head" value={<Digest h={s.head} />} />
        <Field label="session" value={<span className="font-mono text-[12px]">{s.session_id || "\u2014"}</span>} />
        <Field label="last verdict" value={<Verdict v={s.last_verdict} />} />
        <Field label="receipts" value={<span className="font-mono text-[12.5px]">{s.receipt_count ?? 0}</span>} />
        <Field label="verdict latency" value={<span className="font-mono text-[12.5px]">{ms(s.last_latency_ms)}</span>} tone="warn" />
      </div>

      {/* one bar with every control */}
      <div className="space-y-2 rounded-window border border-gridline bg-white px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <Action label="create demo repository" path="/api/repo/demo" onDone={refreshAll} variant="primary" />
          <Action label="protect" path="/api/repo/protect" onDone={refreshAll} />
          <Action label="stop protection" path="/api/repo/stop" onDone={refreshAll} confirm="Remove the Countersign hook from this repository settings file?" />
          <Action label="refresh git state" path="/api/repo/refresh" onDone={refreshAll} />
          <span className="mx-1 h-5 w-px bg-gridline" />
          <input
            value={connectPath}
            onChange={(e) => setConnectPath(e.target.value)}
            placeholder="/absolute/path/to/a/git/repository"
            className="min-w-[220px] flex-1 rounded-[6px] border border-gridline bg-white px-2 py-[6px] font-mono text-[11.5px] outline-none focus:border-ember"
          />
          <Action label="connect" path="/api/repo/connect" body={{ path: connectPath }} onDone={refreshAll} disabled={!connectPath.trim()} />
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-gridline pt-2">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-slate">manual</span>
          <Action label="start session" path="/api/session/start" onDone={refreshAll} />
          <Action label="record read" path="/api/evidence/read" body={{ path: opPath }} onDone={refreshAll} />
          <Action label="attempt edit" path="/api/interceptor/attempt" body={{ path: opPath, tool: "apply_diff" }} onDone={refreshAll} variant="danger" />
          <input
            value={opPath}
            onChange={(e) => setOpPath(e.target.value)}
            placeholder="path"
            className="min-w-[160px] max-w-[260px] flex-1 rounded-[6px] border border-gridline bg-white px-2 py-[6px] font-mono text-[11.5px] outline-none focus:border-ember"
          />
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          <AgentTurn onDone={refreshAll} />

          <StalePanel />

          <Panel
            title="held vs on disk"
            right={
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                {evidence.data?.counts.total ?? 0} held &middot; {evidence.data?.counts.stale ?? 0} stale
              </span>
            }
          >
            {watch.length === 0 ? (
              <Empty>Nothing held yet.</Empty>
            ) : (
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">path</th>
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">held</th>
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">on disk</th>
                    <th className="border-b border-gridline pb-1 font-normal">status</th>
                  </tr>
                </thead>
                <tbody>
                  {watch.map((r) => (
                    <tr key={r.path + r.type} className="align-baseline">
                      <td className="border-b border-gridline/60 py-[6px] pr-2 font-mono text-[12px]">{r.path}</td>
                      <td className="border-b border-gridline/60 py-[6px] pr-2"><Digest h={r.held_digest} /></td>
                      <td className="border-b border-gridline/60 py-[6px] pr-2"><Digest h={r.current_digest} /></td>
                      <td className="border-b border-gridline/60 py-[6px]"><StatusPill status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {staleRows.length > 0 ? (
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-[11.5px] uppercase tracking-[0.1em] text-ember-text">
                  the next edit on these paths is refused
                </span>
                <span className="flex gap-2">
                  <Action label="refresh evidence" path="/api/evidence/refresh" onDone={refreshAll} variant="danger" />
                  <Action label="re-check" path="/api/evidence/recheck" body={{ path: staleRows[0].path }} onDone={refreshAll} />
                </span>
              </div>
            ) : null}
          </Panel>

          <Panel
            title="last intercepted call"
            right={
              <Link href="/console/interceptor" className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                all calls
              </Link>
            }
          >
            {!last ? (
              <Empty>No call yet.</Empty>
            ) : (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                  <Field label="tool" value={<span className="font-mono text-[12.5px]">{last.tool}</span>} />
                  <Field label="class" value={<span className="font-mono text-[11.5px]">{last.classification}</span>} />
                  <Field label="target" value={<span className="font-mono text-[12.5px]">{last.path || "\u2014"}</span>} />
                  <Field label="verdict" value={<Verdict v={last.verdict} />} />
                  <Field label="exit" value={<span className="font-mono text-[12.5px]">{last.exit_code}</span>} tone={last.exit_code === 2 ? "warn" : "plain"} />
                  <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(last.latency_ms)}</span>} />
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-gridline pt-2">
                  <Field label="held" value={<Digest h={last.held_digest} />} />
                  <Field label="on disk" value={<Digest h={last.current_digest} />} />
                  <span className="font-mono text-[11.5px] text-slate">
                    {stamp(last.at)} &middot; {last.reason_code || "none"} &middot; {last.receipt_id || "no receipt"}
                  </span>
                  {last.receipt_id ? (
                    <Link href={`/console/receipts?open=${last.receipt_id}`} className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                      open receipt
                    </Link>
                  ) : null}
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-3">
          <Panel title="repository">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <Field label="path" value={<span className="font-mono text-[11.5px]">{s.repository || "\u2014"}</span>} />
              <Field label="commits" value={<span className="font-mono text-[12.5px]">{repo.data?.commits || "\u2014"}</span>} />
              <Field label="hook" value={<span className="font-mono text-[12px]">{s.hook_scope?.scope || "not installed"}</span>} />
              <Field label="held files" value={<span className="font-mono text-[12.5px]">{repo.data?.protected_files?.length ?? 0}</span>} />
              <Field
                label="working tree"
                value={
                  <span className="font-mono text-[11.5px]">
                    {repo.data?.working_tree?.clean
                      ? "clean"
                      : `${repo.data?.working_tree?.changed?.length ?? 0} changed: ${(repo.data?.working_tree?.changed || []).slice(0, 2).join(", ")}`}
                  </span>
                }
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-gridline pt-3">
              {[
                ["hook", sec?.hook_installed],
                ["runtime", sec?.runtime_connected],
                ["protected", sec?.repository_protected],
                ["chain", sec?.receipt_chain?.valid],
                ["session", sec?.session_valid],
              ].map(([label, ok]) => (
                <span key={String(label)} className="flex items-center gap-2 font-mono text-[11.5px]">
                  <span className={`inline-block h-[7px] w-[7px] rounded-full ${ok ? "bg-emerald-500" : "bg-ember"}`} />
                  <span className="text-graphite">{String(label)}</span>
                  <span className="text-slate">{ok ? "ok" : "no"}</span>
                </span>
              ))}
              <span className="font-mono text-[11.5px] text-slate">
                chain {sec?.receipt_chain?.count ?? 0} receipts
              </span>
            </div>
          </Panel>

          <Panel
            title="last receipt"
            right={
              <Link href="/console/receipts" className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                receipt log
              </Link>
            }
          >
            {!lastReceipt ? (
              <Empty>No receipt yet.</Empty>
            ) : (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                  <Field label="id" value={<span className="font-mono text-[11.5px]">{lastReceipt.receipt_id}</span>} />
                  <Field label="verdict" value={<Verdict v={lastReceipt.verdict} />} />
                  <Field label="exit" value={<span className="font-mono text-[12.5px]">{lastReceipt.exit_code}</span>} />
                  <Field label="written" value={<span className="font-mono text-[12px]">{stamp(lastReceipt.timestamp)}</span>} />
                </div>
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-gridline pt-2">
                  <Field label="hash" value={<Digest h={lastReceipt.receipt_hash} />} />
                  <Field label="chains to" value={<Digest h={lastReceipt.previous_receipt_hash} />} />
                </div>
              </div>
            )}
          </Panel>

          <Panel title="live events">
            {events.length === 0 ? (
              <Empty>Quiet.</Empty>
            ) : (
              <ul className="space-y-[3px] font-mono text-[11.5px]">
                {events.slice(0, 8).map((e, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-mist">{stamp(e.at as string)}</span>
                    <span className="text-graphite">
                      {e.event === "gate_event"
                        ? String((e.record as { event?: string })?.event || "gate_event")
                        : String(e.event)}
                    </span>
                    <span className="truncate text-slate">
                      {String(
                        (e.record as { path?: string })?.path ||
                          (e.path as string) ||
                          (e.receipt_id as string) ||
                          ((e.codes as string[]) || []).join(" ") ||
                          (e.receipt as string) ||
                          (e.session_id as string) ||
                          ""
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-window border border-gridline bg-white px-3 py-2">
        <span className="font-mono text-[11.5px] text-slate">
          last verdict {humanAge(last?.at)} &middot; {dig(s.last_receipt_hash, 10)}
        </span>
        <Link
          href="/console/self-test"
          className="rounded-pill border border-ember bg-ember px-4 py-[6px] font-mono text-[12px] uppercase tracking-[0.08em] text-white"
        >
          self-test
        </Link>
      </div>

      {lastReceipt ? (
        <details className="rounded-window border border-gridline bg-white">
          <summary className="cursor-pointer px-3 py-2 font-mono text-[11.5px] uppercase tracking-[0.12em] text-graphite">
            receipt json
          </summary>
          <div className="px-3 pb-3">
            <JsonBlock value={lastReceipt} max={14} />
          </div>
        </details>
      ) : null}
    </div>
  );
}
