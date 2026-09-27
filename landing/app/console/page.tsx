"use client";

// PROTECT: the operational homepage. Everything on it is read from the runtime, and
// every control performs a real operation on a real repository.

import Link from "next/link";
import { useState } from "react";
import { Action, Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, StatusPill, Verdict } from "@/components/console";
import { useApi, useEvents, dateTime, dig, humanAge, ms, stamp } from "@/lib/runtime";

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
  const events = useEvents(12);

  const s = status.data || {};
  const rows = evidence.data?.rows || [];
  const calls = interceptor.data?.rows || [];
  const last = calls[0];
  const lastReceipt = receipts.data?.rows?.[0];
  const staleRows = rows.filter((r) => r.status === "STALE");
  const watch = rows.filter((r) => r.type === "file_read").slice(0, 6);

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

      {/* status bar */}
      <div className="grid grid-cols-2 gap-3 rounded-window border border-gridline bg-white px-3 py-3 md:grid-cols-4 xl:grid-cols-8">
        <Field
          label="countersign"
          value={
            s.disconnected ? (
              <span className="font-mono text-[12.5px] text-ember-text">DISCONNECTED</span>
            ) : s.protected ? (
              <span className="font-mono text-[12.5px] text-ink">PROTECTED</span>
            ) : (
              <span className="font-mono text-[12.5px] text-ember-text">RUNTIME UP, HOOK OFF</span>
            )
          }
        />
        <Field label="repository" value={<span className="font-mono text-[12px]">{s.repository ? s.repository.split("/").slice(-2).join("/") : "\u2014"}</span>} />
        <Field label="branch" value={<span className="font-mono text-[12.5px]">{s.branch || "\u2014"}</span>} />
        <Field label="head" value={<Digest h={s.head} />} />
        <Field label="session" value={<span className="font-mono text-[12px]">{s.session_id || "\u2014"}</span>} />
        <Field label="last verdict" value={<Verdict v={s.last_verdict} />} />
        <Field
          label="last receipt"
          value={<span className="font-mono text-[11.5px]">{s.last_receipt_id || "\u2014"}</span>}
        />
        <Field label="runtime latency" value={<span className="font-mono text-[12.5px]">{ms(s.last_latency_ms)}</span>} tone="warn" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          {/* held vs current */}
          <Panel
            title="held evidence vs current repository"
            right={
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                {evidence.data?.counts.total ?? 0} held &middot; {evidence.data?.counts.stale ?? 0} stale
              </span>
            }
          >
            {watch.length === 0 ? (
              <Empty>
                No evidence held yet. Start a session and let the agent read a file through the
                hook; the digest it records appears here.
              </Empty>
            ) : (
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">path</th>
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">held sha256</th>
                    <th className="border-b border-gridline pb-1 pr-2 font-normal">current sha256</th>
                    <th className="border-b border-gridline pb-1 font-normal">status</th>
                  </tr>
                </thead>
                <tbody>
                  {watch.map((r) => (
                    <tr key={r.path + r.type} className="align-baseline">
                      <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px]">
                        {r.path}
                      </td>
                      <td className="border-b border-gridline/60 py-[7px] pr-2"><Digest h={r.held_digest} /></td>
                      <td className="border-b border-gridline/60 py-[7px] pr-2"><Digest h={r.current_digest} /></td>
                      <td className="border-b border-gridline/60 py-[7px]"><StatusPill status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {staleRows.length > 0 ? (
              <div className="mt-3 flex items-center justify-between rounded-window border border-ember/40 bg-ember-glow/30 px-3 py-2">
                <div className="font-mono text-[12px] uppercase tracking-[0.12em] text-ember-text">
                  held digest differs from the repository &rarr; the next state-changing call on
                  these paths is refused
                </div>
                <Action label="refresh evidence" path="/api/evidence/refresh" onDone={refreshAll} variant="danger" />
              </div>
            ) : null}
          </Panel>

          {/* stale evidence panel */}
          {staleRows.length > 0 ? (
            <Panel title="stale evidence detected" tone="alert">
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="agent held" value={<Digest h={staleRows[0].held_digest} />} tone="warn" />
                <Field label="repository now" value={<Digest h={staleRows[0].current_digest} />} />
                <Field label="changed path" value={<span className="font-mono text-[12.5px]">{staleRows[0].path}</span>} />
                <Field label="detected" value={<span className="font-mono text-[12.5px]">{dateTime(staleRows[0].read_at)} vs now</span>} />
                <Field label="affects" value={<span className="font-mono text-[12.5px]">{last?.path || staleRows[0].path}</span>} />
                <Field label="verdict for that path" value={<Verdict v={last?.verdict || "REFUSED"} />} />
              </div>
              <ol className="mt-3 space-y-1 border-t border-gridline pt-2 font-mono text-[12px] text-graphite">
                <li>1. re-read the affected evidence through the hook</li>
                <li>2. recompute the digest</li>
                <li>3. refresh the task evidence manifest</li>
                <li>4. retry the operation</li>
              </ol>
              <div className="mt-2 flex gap-2">
                <Action label="refresh evidence now" path="/api/evidence/refresh" onDone={refreshAll} variant="primary" />
                <Action label="re-check" path="/api/evidence/recheck" body={{ path: staleRows[0].path }} onDone={refreshAll} />
              </div>
            </Panel>
          ) : null}

          {/* latest intercepted call */}
          <Panel
            title="latest intercepted call"
            right={
              <Link href="/console/interceptor" className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                all calls
              </Link>
            }
          >
            {!last ? (
              <Empty>No tool call has reached the gate in this repository yet.</Empty>
            ) : (
              <div className="space-y-3">
                <div className="grid gap-3 md:grid-cols-4">
                  <Field label="tool" value={<span className="font-mono text-[12.5px]">{last.tool}</span>} />
                  <Field label="operation class" value={<span className="font-mono text-[11.5px]">{last.classification}</span>} />
                  <Field label="target" value={<span className="font-mono text-[12.5px]">{last.path || "\u2014"}</span>} />
                  <Field label="verdict" value={<Verdict v={last.verdict} />} />
                  <Field label="held digest" value={<Digest h={last.held_digest} />} />
                  <Field label="current digest" value={<Digest h={last.current_digest} />} />
                  <Field label="exit code" value={<span className="font-mono text-[12.5px]">{last.exit_code}</span>} tone={last.exit_code === 2 ? "warn" : "plain"} />
                  <Field label="latency" value={<span className="font-mono text-[12.5px]">{ms(last.latency_ms)}</span>} />
                </div>
                <div className="flex items-center justify-between border-t border-gridline pt-2">
                  <span className="font-mono text-[11.5px] text-slate">
                    {stamp(last.at)} &middot; {last.reason_code || "no reason code"} &middot;{" "}
                    {last.receipt_id ? `receipt ${last.receipt_id}` : "no receipt"}
                  </span>
                  {last.receipt_id ? (
                    <Link href={`/console/receipts?open=${last.receipt_id}`} className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                      inspect receipt
                    </Link>
                  ) : null}
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-3">
          {/* repository */}
          <Panel title="repository">
            <div className="grid grid-cols-2 gap-3">
              <Field label="path" value={<span className="font-mono text-[11.5px]">{s.repository || "\u2014"}</span>} />
              <Field label="commits" value={<span className="font-mono text-[12.5px]">{repo.data?.commits || "\u2014"}</span>} />
              <Field label="hook" value={<span className="font-mono text-[12px]">{s.hook_scope?.scope || "not installed"}</span>} />
              <Field label="protected files" value={<span className="font-mono text-[12.5px]">{repo.data?.protected_files?.length ?? 0}</span>} />
            </div>
            <div className="mt-3 border-t border-gridline pt-2">
              <Field
                label="working tree"
                value={
                  <span className="font-mono text-[11.5px]">
                    {repo.data?.working_tree?.clean
                      ? "clean"
                      : `${repo.data?.working_tree?.changed?.length ?? 0} changed: ${(repo.data?.working_tree?.changed || []).slice(0, 3).join(", ")}`}
                  </span>
                }
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2 border-t border-gridline pt-3">
              <Action label="protect" path="/api/repo/protect" onDone={refreshAll} variant="primary" />
              <Action label="stop protection" path="/api/repo/stop" onDone={refreshAll} confirm="Remove the Countersign hook from this repository settings file?" />
              <Action label="refresh git state" path="/api/repo/refresh" onDone={refreshAll} />
              <Action label="create demo repository" path="/api/repo/demo" onDone={refreshAll} />
              <Action label="start demo" path="/api/demo/start" onDone={refreshAll} />
            </div>
            <div className="mt-3 flex gap-2 border-t border-gridline pt-3">
              <input
                value={connectPath}
                onChange={(e) => setConnectPath(e.target.value)}
                placeholder="/absolute/path/to/a/git/repository"
                className="min-w-0 flex-1 rounded-[6px] border border-gridline bg-white px-2 py-[6px] font-mono text-[11.5px] outline-none focus:border-ember"
              />
              <Action
                label="connect repository"
                path="/api/repo/connect"
                body={{ path: connectPath }}
                onDone={refreshAll}
                disabled={!connectPath.trim()}
              />
            </div>
          </Panel>

          {/* operator actions: the same gate command the agent's hook runs */}
          <Panel
            title="operator actions"
            right={
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                same command the agent hook runs
              </span>
            }
          >
            <div className="flex flex-wrap items-center gap-2">
              <Action label="start session" path="/api/session/start" onDone={refreshAll} />
              <Action label="record read" path="/api/evidence/read" body={{ path: opPath }} onDone={refreshAll} />
              <Action label="attempt edit" path="/api/interceptor/attempt" body={{ path: opPath, tool: "apply_diff" }} onDone={refreshAll} variant="danger" />
              <input
                value={opPath}
                onChange={(e) => setOpPath(e.target.value)}
                placeholder="path inside the repository"
                className="min-w-[180px] flex-1 rounded-[6px] border border-gridline bg-white px-2 py-[6px] font-mono text-[11.5px] outline-none focus:border-ember"
              />
            </div>
            <div className="mt-2 font-mono text-[11px] text-slate">
              these call the hook command with the payload the agent sends, so an operator can
              walk the whole loop without an agent attached
            </div>
          </Panel>

          {/* security */}
          <Panel
            title="security state"
            right={
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                {security.data?.verdict_path || ""}
              </span>
            }
          >
            <ul className="space-y-[6px] font-mono text-[12px]">
              {[
                ["hook installed", security.data?.hook_installed, security.data?.hook_scope || ""],
                ["runtime connected", security.data?.runtime_connected, `:${s.runtime?.port ?? ""}`],
                ["repository protected", security.data?.repository_protected, s.hook_scope?.scope || ""],
                ["receipt chain valid", security.data?.receipt_chain?.valid, `${security.data?.receipt_chain?.count ?? 0} receipts`],
                ["session valid", security.data?.session_valid, s.session_id || ""],
              ].map(([label, ok, note]) => (
                <li key={String(label)} className="flex items-center gap-2">
                  <span
                    className={`inline-block h-[7px] w-[7px] rounded-full ${
                      ok ? "bg-emerald-500" : "bg-ember"
                    }`}
                  />
                  <span className="min-w-[168px] text-graphite">{String(label)}</span>
                  <span className="text-slate">{String(ok ? "true" : "false")}</span>
                  <span className="truncate text-mist">{String(note || "")}</span>
                </li>
              ))}
            </ul>
          </Panel>

          {/* latest receipt */}
          <Panel
            title="latest receipt"
            right={
              <Link href="/console/receipts" className="font-mono text-[11px] uppercase tracking-[0.12em] text-ember-text">
                receipt log
              </Link>
            }
          >
            {!lastReceipt ? (
              <Empty>No receipt has been written in this repository yet.</Empty>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <Field label="receipt id" value={<span className="font-mono text-[11.5px]">{lastReceipt.receipt_id}</span>} />
                <Field label="verdict" value={<Verdict v={lastReceipt.verdict} />} />
                <Field label="hash" value={<Digest h={lastReceipt.receipt_hash} />} />
                <Field label="chain back to" value={<Digest h={lastReceipt.previous_receipt_hash} />} />
                <Field label="written" value={<span className="font-mono text-[12px]">{stamp(lastReceipt.timestamp)}</span>} />
                <Field label="exit code" value={<span className="font-mono text-[12.5px]">{lastReceipt.exit_code}</span>} />
              </div>
            )}
          </Panel>

          {/* live events */}
          <Panel title="live events (runtime stream)">
            {events.length === 0 ? (
              <Empty>Waiting for the runtime stream. Events appear as the gate writes them.</Empty>
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
                          (e.detail as string) ||
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

      {/* self-test call to action */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-window border border-gridline bg-white px-4 py-3">
        <div>
          <div className="text-heading-sm">Run the whole mechanism now</div>
          <div className="text-[13px] text-slate">
            Builds a real repository, reads a file through the gate, changes it from a second
            process, attempts the edit, refreshes, retries. Both attempts are persisted.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/console/self-test"
            className="rounded-pill border border-ember bg-ember px-4 py-[7px] font-mono text-[12px] uppercase tracking-[0.08em] text-white"
          >
            run self-test
          </Link>
          <span className="font-mono text-[11px] text-slate">
            last verdict {humanAge(last?.at)} &middot; {dig(s.last_receipt_hash, 10)}
          </span>
        </div>
      </div>

      {lastReceipt ? (
        <details className="rounded-window border border-gridline bg-white">
          <summary className="cursor-pointer px-3 py-2 font-mono text-[11.5px] uppercase tracking-[0.12em] text-graphite">
            latest receipt json
          </summary>
          <div className="px-3 pb-3">
            <JsonBlock value={lastReceipt} max={14} />
          </div>
        </details>
      ) : null}
    </div>
  );
}
