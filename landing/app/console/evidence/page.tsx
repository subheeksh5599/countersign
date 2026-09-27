"use client";

// EVIDENCE: exactly what the active session holds, and what the repository says now.

import { useState } from "react";
import { Action, Digest, Empty, Field, JsonBlock, Panel, RuntimeBanner, StatusPill } from "@/components/console";
import { useApi, dateTime, dig, humanAge } from "@/lib/runtime";

type EvRow = {
  path: string; type: string; held_digest: string | null; current_digest: string | null;
  git_revision: string | null; read_at: string | null; verified_at: string | null;
  via: string; status: string;
};
type Session = {
  session_id?: string | null; agent?: string; started?: string | null; commit?: string | null;
  implicit?: boolean; evidence?: { total: number; stale: number; current: number; deleted: number };
};

type SessionRow = {
  session_id: string;
  opened_at?: string | null;
  files?: string[];
  file_count?: number;
  observations?: number;
  refusals?: number;
  admissions?: number;
  receipts?: number;
  active?: boolean;
  implicit?: boolean;
};

const FILTERS = ["all", "current", "stale", "deleted"] as const;

export default function EvidencePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [pick, setPick] = useState<string | null>(null);
  const session = useApi<Session>("/api/session");
  const sessions = useApi<{ rows: SessionRow[]; count: number; active: string | null }>(
    "/api/sessions"
  );
  const ev = useApi<{ rows: EvRow[]; counts: Record<string, number>; session_id: string | null }>(
    `/api/evidence?filter=${filter}${pick ? `&session=${pick}` : ""}`
  );

  const reload = () => {
    ev.reload();
    session.reload();
    sessions.reload();
  };
  const shown =
    (sessions.data?.rows || []).find((s) => s.session_id === pick) || null;
  const rows = ev.data?.rows || [];
  const selected = rows.find((r) => r.path === open) || null;

  return (
    <div className="space-y-3">
      <RuntimeBanner error={ev.error} />

      {/* every manifest this repository has, not only the newest one */}
      <Panel
        title="sessions in this store"
        right={
          <span className="font-mono text-caption uppercase tracking-[0.14em] text-graphite">
            {sessions.data?.count ?? 0} manifests
          </span>
        }
      >
        {!sessions.data?.count ? (
          <Empty>No manifest has been opened in this repository yet.</Empty>
        ) : (
          <div className="overflow-hidden rounded-window border border-gridline">
            <table className="w-full text-left">
              <thead className="bg-vellum">
                <tr className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
                  <th className="px-2 py-[6px]">session</th>
                  <th className="px-2 py-[6px]">opened</th>
                  <th className="px-2 py-[6px]">files</th>
                  <th className="px-2 py-[6px]">observations</th>
                  <th className="px-2 py-[6px]">refused</th>
                  <th className="px-2 py-[6px]">allowed</th>
                  <th className="px-2 py-[6px]">receipts</th>
                  <th className="px-2 py-[6px]" />
                </tr>
              </thead>
              <tbody>
                {(sessions.data?.rows || []).map((s) => (
                  <tr key={s.session_id} className="border-t border-gridline/70">
                    <td className="px-2 py-[6px] font-mono text-[11.5px] text-ink">
                      {s.session_id}
                      {s.active ? <span className="ml-2 text-ember-text">active</span> : null}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                      {dateTime(s.opened_at)}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                      {s.file_count}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                      {s.observations}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-ember-text">
                      {s.refusals}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                      {s.admissions}
                    </td>
                    <td className="px-2 py-[6px] font-mono text-[12px] text-graphite">
                      {s.receipts}
                    </td>
                    <td className="px-2 py-[6px] text-right">
                      <button
                        type="button"
                        onClick={() => setPick(pick === s.session_id ? null : s.session_id)}
                        className={`rounded-pill border px-2 py-[3px] font-mono text-[11px] uppercase tracking-[0.1em] ${
                          pick === s.session_id
                            ? "border-ink bg-white text-ink"
                            : "border-gridline bg-white text-slate"
                        }`}
                      >
                        {pick === s.session_id ? "shown" : "inspect"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {pick ? (
          <div className="mt-3 flex items-center gap-3 text-body text-graphite">
            <span className="font-mono text-[12px]">
              inspecting {pick} ({shown?.file_count ?? 0} files, {shown?.receipts ?? 0} receipts)
            </span>
            <button
              type="button"
              onClick={() => setPick(null)}
              className="rounded-pill border border-gridline bg-white px-2 py-[3px] font-mono text-[11px] uppercase tracking-[0.1em] text-slate"
            >
              back to the active session
            </button>
          </div>
        ) : null}
      </Panel>

      <Panel
        title={pick ? "session inspected" : "current session"}
        right={
          <Action
            label="refresh manifest"
            path="/api/evidence/refresh"
            body={pick ? { session: pick } : {}}
            onDone={reload}
          />
        }
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Field label="session" value={<span className="font-mono text-[12px]">{pick || session.data?.session_id || "\u2014"}</span>} />
          <Field label="agent" value={<span className="font-mono text-[12.5px]">{session.data?.agent || "\u2014"}</span>} />
          <Field label="started" value={<span className="font-mono text-[12px]">{dateTime(session.data?.started)}</span>} />
          <Field label="commit" value={<Digest h={session.data?.commit} />} />
          <Field label="evidence count" value={<span className="font-mono text-[12.5px]">{ev.data?.counts.total ?? 0}</span>} />
          <Field
            label="stale count"
            value={<span className="font-mono text-[12.5px]">{ev.data?.counts.stale ?? 0}</span>}
            tone={(ev.data?.counts.stale ?? 0) > 0 ? "warn" : "plain"}
          />
        </div>
      </Panel>

      <Panel
        title="evidence held by this session"
        right={
          <div className="flex gap-1">
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
            {filter === "all"
              ? "Nothing yet."
              : `No evidence item is currently ${filter}.`}
          </Empty>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="font-mono text-caption uppercase tracking-[0.14em] text-slate">
                <th className="border-b border-gridline pb-1 pr-2 font-normal">path</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">type</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">held sha256</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">current sha256</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">git revision</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">last read</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">last verified</th>
                <th className="border-b border-gridline pb-1 pr-2 font-normal">status</th>
                <th className="border-b border-gridline pb-1 font-normal">actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.path + r.type} className={open === r.path ? "bg-vellum" : ""}>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[12px]">
                    <button type="button" onClick={() => setOpen(open === r.path ? null : r.path)} className="hover:text-ember-text">
                      {r.path}
                    </button>
                  </td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{r.type}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><Digest h={r.held_digest} /></td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><Digest h={r.current_digest} /></td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><Digest h={r.git_revision} /></td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{humanAge(r.read_at)}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2 font-mono text-[11.5px] text-graphite">{humanAge(r.verified_at)}</td>
                  <td className="border-b border-gridline/60 py-[7px] pr-2"><StatusPill status={r.status} /></td>
                  <td className="border-b border-gridline/60 py-[7px]">
                    <div className="flex gap-2">
                      <Action label="re-check" path="/api/evidence/recheck" body={{ path: r.path }} onDone={reload} />
                      <Action label="refresh" path="/api/evidence/refresh" body={{ path: r.path }} onDone={reload} variant="danger" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {selected ? (
        <Panel
          title={`evidence detail \u2014 ${selected.path}`}
          right={
            <button type="button" onClick={() => setOpen(null)} className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
              close
            </button>
          }
        >
          <div className="grid gap-3 md:grid-cols-3">
            <Field label="held sha256" value={<span className="font-mono text-[11.5px] break-all">{selected.held_digest || "\u2014"}</span>} tone={selected.status === "STALE" ? "warn" : "plain"} />
            <Field label="current sha256" value={<span className="font-mono text-[11.5px] break-all">{selected.current_digest || "file missing"}</span>} />
            <Field label="status" value={<StatusPill status={selected.status} />} />
            <Field label="recorded via" value={<span className="font-mono text-[12px]">{selected.via}</span>} />
            <Field label="git revision at read" value={<span className="font-mono text-[11.5px]">{selected.git_revision || "not committed at read time"}</span>} />
            <Field label="read at" value={<span className="font-mono text-[12px]">{dateTime(selected.read_at)}</span>} />
          </div>
          <div className="mt-3 border-t border-gridline pt-2 font-mono text-[11.5px] text-graphite">
            held {dig(selected.held_digest, 16)} &rarr; current {dig(selected.current_digest, 16)}
            {selected.held_digest === selected.current_digest
              ? " \u00b7 identical, the call may proceed"
              : " \u00b7 different, a state-changing call on this path is refused"}
          </div>
          <div className="mt-2">
            <JsonBlock value={selected} max={12} />
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
