"use client";

// Operational controls for the console. Everything here drives the real runtime: an agent
// turn runs a real agent against the protected repository, the replay runs the gate's
// replay mode, and the staleness panel reads the store the watcher writes.

import { useState } from "react";
import { Digest, Empty, Field, JsonBlock, Panel, StatusPill, Verdict } from "@/components/console";
import { post, useApi, dateTime, humanAge } from "@/lib/runtime";

type TurnStep = {
  step?: string;
  exit_code?: number | null;
  verdict?: string;
  path?: string;
  detail?: string;
  constant?: string;
  value?: string;
  seconds?: number;
};

type TurnResult = {
  driver?: string;
  session_id?: string;
  exit_code?: number;
  duration_ms?: number;
  receipts_written?: number;
  refused?: boolean;
  steps?: TurnStep[];
  verdicts?: {
    receipt_id?: string;
    verdict?: string;
    reason_code?: string;
    latency_ms?: number | null;
    affected_paths?: string[];
  }[];
  output?: string;
  error?: string;
};

export function AgentTurn({ onDone }: { onDone?: () => void }) {
  const [driver, setDriver] = useState("auto");
  const [prompt, setPrompt] = useState("set RETRY_LIMIT to 5 in src/config.ts");
  const [writer, setWriter] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TurnResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    setResult(null);
    // a turn can legitimately take minutes with a vendor driver, so the guard is long,
    // but the control must never sit in "running" with no way out
    const ac = new AbortController();
    const guard = setTimeout(() => ac.abort(), 180000);
    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_COUNTERSIGN_API || "http://127.0.0.1:4319"}/api/agent/turn`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ driver, prompt, concurrent_writer: writer }),
          signal: ac.signal,
        }
      );
      const j = (await r.json()) as TurnResult;
      setResult(j);
      if (j.error) setErr(j.error);
      onDone?.();
    } catch (e) {
      setErr(
        e instanceof Error && e.name === "AbortError"
          ? "the turn did not answer within three minutes; nothing is claimed about it"
          : e instanceof Error
          ? e.message
          : "the runtime did not answer"
      );
    } finally {
      clearTimeout(guard);
      setBusy(false);
    }
  };

  return (
    <Panel
      title="run an agent turn"
      tone={result?.refused ? "alert" : "plain"}
      right={
        result ? (
          <span className="font-mono text-caption uppercase tracking-[0.14em] text-graphite">
            {result.driver} &middot; exit {result.exit_code}
          </span>
        ) : null
      }
    >
      <label className="mb-1 block font-mono text-caption uppercase tracking-[0.14em] text-slate">
        request
      </label>
      <input
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="mb-3 w-full rounded-none border border-gridline bg-white px-2 py-2 font-mono text-[12.5px] text-ink outline-none focus:border-ink"
      />

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
          driver
          <select
            value={driver}
            onChange={(e) => setDriver(e.target.value)}
            className="ml-2 border border-gridline bg-white px-2 py-1 font-mono text-[12px] text-ink"
          >
            <option value="auto">auto</option>
            <option value="reference">reference agent</option>
            <option value="vendor">vendor CLI</option>
          </select>
        </label>
        <label
          className="flex items-center gap-2 text-body text-graphite"
          title="start a real second process that rewrites the file between the agent's read and its attempt"
        >
          <input type="checkbox" checked={writer} onChange={(e) => setWriter(e.target.checked)} />
          second writer moves the file
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={run}
          className="rounded-pill border border-ember bg-ember px-4 py-[7px] font-mono text-caption uppercase tracking-[0.14em] text-white disabled:opacity-50"
        >
          {busy ? "running" : "run agent turn"}
        </button>
      </div>

      {err ? <div className="mb-3 text-body text-ember-text">{err}</div> : null}

      {result && !err ? (
        <>
          <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Field label="driver" value={<span className="font-mono text-[12.5px]">{result.driver}</span>} />
            <Field
              label="agent exit"
              value={<span className="font-mono text-[12.5px]">{String(result.exit_code)}</span>}
              tone={result.exit_code === 2 ? "warn" : "plain"}
            />
            <Field
              label="receipts written"
              value={<span className="font-mono text-[12.5px]">{String(result.receipts_written)}</span>}
            />
            <Field
              label="duration"
              value={<span className="font-mono text-[12.5px]">{result.duration_ms} ms</span>}
            />
          </div>

          <div className="mb-3 overflow-hidden rounded-window border border-gridline">
            <table className="w-full text-left">
              <thead className="bg-vellum">
                <tr className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                  <th className="px-2 py-[6px]">step</th>
                  <th className="px-2 py-[6px]">exit</th>
                  <th className="px-2 py-[6px]">verdict</th>
                  <th className="px-2 py-[6px]">detail</th>
                </tr>
              </thead>
              <tbody>
                {(result.steps || [])
                  .filter((s) => s.step)
                  .map((s, i) => (
                    <tr key={i} className="border-t border-gridline/70">
                      <td className="px-2 py-[6px] font-mono text-[12px] text-ink">{s.step}</td>
                      <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                        {s.exit_code === undefined || s.exit_code === null ? "\u2014" : s.exit_code}
                      </td>
                      <td className="px-2 py-[6px]">
                        <Verdict v={s.verdict || null} />
                      </td>
                      <td className="px-2 py-[6px] text-body text-graphite">
                        {s.constant ? `${s.constant} = ${s.value} in ${s.path}` : (s.detail || "")}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {result.verdicts && result.verdicts.length > 0 ? (
            <div className="mb-3">
              <div className="mb-[6px] font-mono text-caption uppercase tracking-[0.14em] text-slate">
                receipts this turn produced
              </div>
              {result.verdicts.map((v, i) => (
                <div key={i} className="flex flex-wrap items-center gap-3 border-t border-gridline/70 py-[6px]">
                  <Verdict v={v.verdict || null} />
                  <span className="font-mono text-[12px] text-graphite">{v.reason_code}</span>
                  <span className="font-mono text-[12px] text-slate">{v.latency_ms} ms</span>
                  <span className="font-mono text-[12px] text-slate">{v.receipt_id}</span>
                  <span className="font-mono text-[12px] text-graphite">
                    {(v.affected_paths || []).join(", ")}
                  </span>
                </div>
              ))}
            </div>
          ) : null}

          {result.output ? <JsonBlock value={{ agent_output: result.output }} max={8} /> : null}
        </>
      ) : null}
    </Panel>
  );
}

type ReplayRow = {
  receipt_id?: string;
  verdict?: string;
  reason_code?: string;
  checks?: Record<string, boolean>;
  notes?: string[];
  tree?: string;
  ok?: boolean;
};

export function ReplayPanel() {
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<{
    summary?: { receipts?: number; failures?: number; chain_head?: string | null; ok?: boolean };
    receipts?: ReplayRow[];
    exit_code?: number;
    error?: string;
  } | null>(null);

  const run = async () => {
    setBusy(true);
    try {
      setReport(await post("/api/receipts/replay", {}));
    } catch (e) {
      setReport({ error: e instanceof Error ? e.message : "replay failed" });
    } finally {
      setBusy(false);
    }
  };

  const s = report?.summary;
  return (
    <Panel
      title="replay receipts"
      tone={s && !s.ok ? "alert" : "plain"}
      right={
        s ? (
          <span className="font-mono text-caption uppercase tracking-[0.14em] text-graphite">
            {s.receipts} receipts &middot; {s.failures} failed
          </span>
        ) : null
      }
    >
      <div className="mb-3 flex items-center gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={run}
          className="rounded-pill border border-ember bg-ember px-4 py-[7px] font-mono text-caption uppercase tracking-[0.14em] text-white disabled:opacity-50"
        >
          {busy ? "replaying" : "replay receipts"}
        </button>
        {report?.exit_code !== undefined ? (
          <span className="font-mono text-[12.5px] text-graphite">
            exit {report.exit_code}
            {report.exit_code === 0 ? " (consistent)" : " (a receipt contradicts itself)"}
          </span>
        ) : null}
      </div>

      {report?.error ? <div className="text-body text-ember-text">{report.error}</div> : null}

      {report?.receipts ? (
        <div className="overflow-hidden rounded-window border border-gridline">
          <table className="w-full text-left">
            <thead className="bg-vellum">
              <tr className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                <th className="px-2 py-[6px]">result</th>
                <th className="px-2 py-[6px]">receipt</th>
                <th className="px-2 py-[6px]">verdict</th>
                <th className="px-2 py-[6px]">hash</th>
                <th className="px-2 py-[6px]">chain</th>
                <th className="px-2 py-[6px]">follows</th>
                <th className="px-2 py-[6px]">tree at that revision</th>
              </tr>
            </thead>
            <tbody>
              {report.receipts.map((r, i) => (
                <tr key={i} className="border-t border-gridline/70">
                  <td className="px-2 py-[6px]">
                    <span
                      className={`font-mono text-[11px] uppercase tracking-[0.1em] ${
                        r.ok ? "text-ink" : "text-ember-text"
                      }`}
                    >
                      {r.ok ? "pass" : "fail"}
                    </span>
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {r.receipt_id}
                  </td>
                  <td className="px-2 py-[6px]">
                    <Verdict v={r.verdict || null} />
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {r.checks?.hash_recomputes ? "yes" : "NO"}
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {r.checks?.chain_links ? "yes" : "NO"}
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {r.checks?.verdict_follows_from_inputs ? "yes" : "NO"}
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-slate">{r.tree}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {s?.chain_head ? (
        <div className="mt-3">
          <Field label="chain head" value={<Digest h={s.chain_head} />} mono />
        </div>
      ) : null}
    </Panel>
  );
}

type StaleRow = {
  session_id?: string;
  path?: string;
  status?: string;
  held?: string | null;
  current?: string | null;
  detected_at?: string | null;
  last_change_at?: string | null;
  resolved_at?: string | null;
  seconds_open?: number | null;
};

export function StalePanel() {
  const st = useApi<{ rows: StaleRow[]; stale: number; resolved: number }>("/api/stale");
  const rows = st.data?.rows || [];
  const open = rows.filter((r) => !r.resolved_at);
  const closed = rows.filter((r) => r.resolved_at);

  return (
    <Panel
      title="what moved"
      tone={open.length ? "alert" : "plain"}
      right={
        <span className="font-mono text-caption uppercase tracking-[0.14em] text-graphite">
          {st.data?.stale ?? 0} open &middot; {st.data?.resolved ?? 0} resolved
        </span>
      }
    >
      {rows.length === 0 ? (
        <Empty>Holding steady. Nothing has moved.</Empty>
      ) : (
        <div className="overflow-hidden rounded-window border border-gridline">
          <table className="w-full text-left">
            <thead className="bg-vellum">
              <tr className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                <th className="px-2 py-[6px]">state</th>
                <th className="px-2 py-[6px]">path</th>
                <th className="px-2 py-[6px]">held then</th>
                <th className="px-2 py-[6px]">file now</th>
                <th className="px-2 py-[6px]">first seen</th>
                <th className="px-2 py-[6px]">open for</th>
              </tr>
            </thead>
            <tbody>
              {[...open, ...closed].map((r, i) => (
                <tr
                  key={i}
                  className={`border-t border-gridline/70 ${r.resolved_at ? "opacity-60" : ""}`}
                >
                  <td className="px-2 py-[6px]">
                    <StatusPill status={r.resolved_at ? "CURRENT" : r.status} />
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12.5px] text-ink">{r.path}</td>
                  <td className="px-2 py-[6px]">
                    <Digest h={r.held} />
                  </td>
                  <td className="px-2 py-[6px]">
                    <Digest h={r.current} />
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {dateTime(r.detected_at)} <span className="text-slate">({humanAge(r.detected_at)})</span>
                  </td>
                  <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                    {r.resolved_at
                      ? `resolved ${humanAge(r.resolved_at)}`
                      : r.seconds_open !== null && r.seconds_open !== undefined
                      ? `${r.seconds_open}s`
                      : "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
