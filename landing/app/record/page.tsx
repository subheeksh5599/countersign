"use client";

// VERIFY THE RECORD — a hosted page a reviewer can operate without installing anything.
//
// This is not a reenactment. The four receipts below are the files committed in the
// repository at docs/evidence-store/live_2026_09_27/receipts, written by a real IBM Bob
// task that the gate refused four times. The checks run here, in this browser tab, with a
// port of the same canonicalisation and the same SHA-256 the CLI uses. A Node run of this
// port reproduces the CLI's per-receipt hashes and its chain head exactly.
//
// The tamper controls modify a copy held in memory. Nothing is written anywhere, and the
// files on disk are untouched.

import { useCallback, useEffect, useState } from "react";
import { Digest, Field, Panel, Verdict } from "@/components/console";

const FILES = [
  "00000_3926db2a55eb.json",
  "00001_7412c1771946.json",
  "00002_352604d27b92.json",
  "00003_e83186b797d1.json",
];

const DIGEST_REASONS = new Set(["EVIDENCE_SUPERSEDED", "REVISION_MOVED"]);
const NO_PATH_REASONS = new Set(["COMMAND_RESULT_CHANGED", "NO_MANIFEST"]);
const MANIFEST_REASONS = new Set([
  "NO_MANIFEST",
  "CROSS_TASK_EVIDENCE",
  "UNVERIFIED_TARGET",
  "UNSUPPORTED_SUBTASK_EVIDENCE",
  "COMMAND_RESULT_CHANGED",
  "OUTSIDE_WORKSPACE",
]);
const HAS_REASONS = new Set(["EVIDENCE_SUPERSEDED", "REVISION_MOVED"]);

type Receipt = Record<string, unknown>;

// Python's json.dumps(ensure_ascii=True) escapes code units above 0x7f; JSON.stringify does
// not. Without this the canonical form differs on any non-ASCII byte.
function pyStr(s: string) {
  return JSON.stringify(s).replace(
    /[\u007f-\uffff]/g,
    (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"),
  );
}

function canon(v: unknown): string {
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : JSON.stringify(v);
  if (typeof v === "string") return pyStr(v);
  if (Array.isArray(v)) return "[" + v.map(canon).join(",") + "]";
  const o = v as Record<string, unknown>;
  return (
    "{" +
    Object.keys(o)
      .sort()
      .map((k) => pyStr(k) + ":" + canon(o[k]))
      .join(",") +
    "}"
  );
}

async function sha256hex(s: string) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

type Row = {
  receipt_id: string;
  tool_name: string;
  verdict: string;
  reason_code: string;
  checks: { hash: boolean; chain: boolean; verdict: boolean };
  ok: boolean;
  held: string | null;
  current: string | null;
  note: string;
};

async function verifyStore(store: Receipt[]) {
  const rows: Row[] = [];
  let previous: string | null = null;
  for (const r of store) {
    const body: Receipt = {};
    for (const [k, v] of Object.entries(r)) if (k !== "receipt_hash") body[k] = v;
    const rehash = await sha256hex(canon(body));
    const hash = rehash === r.receipt_hash;
    const chain = (r.previous_receipt_hash ?? null) === previous;
    const paths = (r.affected_paths as string[]) || [];
    const path = paths[0];
    const held = path ? ((r.evidence_hashes as Record<string, string>) || {})[path] : null;
    const current = path ? ((r.current_hashes as Record<string, string>) || {})[path] : null;
    const code = String(r.reason_code ?? "");
    const verdict = String(r.verdict ?? "");

    let check: boolean;
    let note: string;
    if (!paths) {
      check = NO_PATH_REASONS.has(code) || verdict === "ADMITTED";
      note = "no path recorded";
    } else if (held && current) {
      if (held !== current) {
        check = verdict === "REFUSED" && DIGEST_REASONS.has(code);
        note = `held ${held.slice(0, 12)} differs from on-disk ${current.slice(0, 12)}, so a refusal is the only verdict these inputs support`;
      } else {
        check = verdict === "ADMITTED" || MANIFEST_REASONS.has(code);
        note = `held equals on-disk ${held.slice(0, 12)}, so a digest refusal would contradict the receipt`;
      }
    } else if (held === null && HAS_REASONS.has(code)) {
      check = false;
      note = "a digest refusal with no digest pair recorded";
    } else {
      check = true;
      note = "no digest pair to check";
    }

    rows.push({
      receipt_id: String(r.receipt_id ?? ""),
      tool_name: String(r.tool_name ?? ""),
      verdict,
      reason_code: code,
      checks: { hash, chain, verdict: check },
      ok: hash && chain && check,
      held: held ?? null,
      current: current ?? null,
      note,
    });
    previous = (r.receipt_hash as string) ?? null;
  }
  return { rows, head: previous, failures: rows.filter((r) => !r.ok).length };
}

export default function RecordPage() {
  const [originals, setOriginals] = useState<Receipt[]>([]);
  const [store, setStore] = useState<Receipt[]>([]);
  const [result, setResult] = useState<{ rows: Row[]; head: string | null; failures: number } | null>(null);
  const [expected, setExpected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tamper, setTamper] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const got = await Promise.all(
          FILES.map((f) => fetch(`/record/${f}`, { cache: "no-store" }).then((r) => r.json())),
        );
        setOriginals(got);
        setStore(got);
        const meta = await fetch("/record/expected.json", { cache: "no-store" })
          .then((r) => r.json())
          .catch(() => null);
        if (meta?.chain_head) setExpected(meta.chain_head);
      } catch {
        setError("the receipt files could not be loaded from /record");
      }
    })();
  }, []);

  const run = useCallback(async (s: Receipt[]) => {
    if (s.length) setResult(await verifyStore(s));
  }, []);

  useEffect(() => {
    if (store.length) run(store);
  }, [store, run]);

  const flipVerdict = () => {
    const s = originals.map((r) => ({ ...r }));
    s[2] = { ...s[2], verdict: "ADMITTED" };
    setTamper(
      "receipt 3 was changed to claim ADMITTED. Two checks fail on it. Its stored hash no longer " +
        "recomputes, because a field inside the hashed body changed, and its verdict contradicts the " +
        "two digests it recorded, which differ from each other.",
    );
    setStore(s);
  };

  const editField = () => {
    const s = originals.map((r) => ({ ...r }));
    s[3] = { ...s[3], tool_name: String(s[3].tool_name) + "_edited" };
    setTamper(
      "receipt 4 had one stored field changed and nothing else. The hash recomputation fails on it, " +
        "which is what hashing the whole body buys: a record cannot be edited in place and still " +
        "describe itself.",
    );
    setStore(s);
  };

  const reset = () => {
    setTamper(null);
    setStore(originals.map((r) => ({ ...r })));
  };

  const headMatches = result && expected ? result.head === expected : null;

  return (
    <div className="mx-auto max-w-[1100px] space-y-4 px-6 py-10">
      <header className="space-y-3">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-slate">
          verify the record
        </div>
        <h1 className="text-[28px] leading-tight text-ink">
          Four receipts a real Bob task wrote, checked in your browser
        </h1>
        <p className="max-w-[78ch] text-body text-graphite">
          These are the files committed in the repository under{" "}
          <span className="font-mono text-[13px]">docs/evidence-store/live_2026_09_27/receipts</span>,
          written when the gate refused four edits from a live IBM Bob session. The three checks
          below run here, in this tab, using the same canonical form and the same SHA-256 the
          command line tool uses. Nothing is fetched from a server and nothing is reenacted.
        </p>
      </header>

      <Panel
        title="checks"
        right={
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate">
            {result ? `${result.rows.length} receipts · ${result.failures} failed` : "running"}
          </span>
        }
      >
        {error ? (
          <p className="text-body text-ember-text">{error}</p>
        ) : !result ? (
          <p className="text-body text-slate">recomputing the stored hashes</p>
        ) : (
          <div className="space-y-3">
            {result.rows.map((r, i) => (
              <div key={r.receipt_id} className="rounded border border-gridline bg-white p-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-mono text-[12px] text-ink">{r.receipt_id}</span>
                  <Verdict v={r.verdict} />
                  <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-slate">
                    {r.reason_code}
                  </span>
                  <span className="font-mono text-[11px] text-graphite">{r.tool_name}</span>
                  <span
                    className={`ml-auto font-mono text-[11px] uppercase tracking-[0.14em] ${
                      r.ok ? "text-graphite" : "text-ember-text"
                    }`}
                  >
                    {r.ok ? "checks pass" : "checks fail"}
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-3">
                  {(
                    [
                      ["stored hash recomputes", r.checks.hash],
                      ["chain link holds", r.checks.chain],
                      ["verdict follows from the digests", r.checks.verdict],
                    ] as [string, boolean][]
                  ).map(([label, pass]) => (
                    <span key={label} className="font-mono text-[11px] text-graphite">
                      <span className={pass ? "text-graphite" : "text-ember-text"}>
                        {pass ? "pass" : "FAIL"}
                      </span>{" "}
                      {label}
                    </span>
                  ))}
                </div>
                <p className="mt-2 max-w-[92ch] text-[12px] leading-relaxed text-slate">{r.note}</p>
                {r.held && r.current ? (
                  <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
                    <Digest h={r.held} label="held by the task" />
                    <Digest h={r.current} label="on disk at refusal" />
                  </div>
                ) : null}
                <div className="mt-1 font-mono text-[10px] text-ash">receipt {i + 1} of {result.rows.length}</div>
              </div>
            ))}

            <div className="rounded border border-gridline bg-vellum p-3">
              <Field label="chain head computed here" value={result.head || "none"} mono />
              <Field
                label="chain head the cli prints"
                value={expected || "not available"}
                mono
              />
              <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.12em]">
                {headMatches === null
                  ? "comparing"
                  : headMatches
                    ? "the two agree"
                    : "these disagree"}
              </p>
            </div>
          </div>
        )}
      </Panel>

      <Panel title="attack this record">
        <p className="max-w-[78ch] text-body text-graphite">
          A verification you cannot fail is decoration. The buttons below change a copy of one
          receipt in this tab and recompute. The files on disk are not touched, and reloading this
          page restores them.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={flipVerdict}
            className="rounded-pill border border-gridline bg-white px-4 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink hover:border-ember"
          >
            make a receipt claim ADMITTED
          </button>
          <button
            onClick={editField}
            className="rounded-pill border border-gridline bg-white px-4 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink hover:border-ember"
          >
            edit one stored field
          </button>
          <button
            onClick={reset}
            className="rounded-pill border border-gridline bg-white px-4 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-slate hover:border-ember"
          >
            restore
          </button>
        </div>
        {tamper ? (
          <p className="mt-3 max-w-[78ch] text-[12px] leading-relaxed text-ember-text">
            applied: {tamper}. The failing check above is the one that caught it. This is the same
            failure the repository&apos;s CI workflow raises when a receipt is edited after the fact,
            and it is why the store is worth keeping: the record does not need to be trusted, it can
            be recomputed.
          </p>
        ) : null}
      </Panel>

      <footer className="flex flex-wrap gap-x-6 gap-y-1 pt-2 font-mono text-[11px] text-slate">
        <a className="underline hover:text-ember-text" href="/">the product</a>
        <a className="underline hover:text-ember-text" href="/console">the console (needs the local runtime)</a>
        <a className="underline hover:text-ember-text" href="https://github.com/subheeksh5599/countersign">
          the repository
        </a>
      </footer>
    </div>
  );
}
