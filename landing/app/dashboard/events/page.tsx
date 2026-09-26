import Link from "next/link";
import { store, short, stamp } from "@/lib/store";

export const metadata = { title: "Event log · Countersign" };

const KINDS = ["all", "verdict", "evidence_recorded", "manifest_opened"];

export default async function Events({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string }>;
}) {
  const { kind } = await searchParams;
  const active = kind && KINDS.includes(kind) ? kind : "all";
  const rows = (active === "all" ? store.events : store.events.filter((e) => e.event === active)).slice(0, 120);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-heading-lg font-medium tracking-[-0.2px]">Event log</h1>
          <p className="mt-2 text-body text-slate">
            The append-only record: {store.totals.events} entries, newest first.
          </p>
        </div>
        <div className="flex gap-2">
          {KINDS.map((k) => (
            <Link
              key={k}
              href={k === "all" ? "/dashboard/events" : `/dashboard/events?kind=${k}`}
              className={`rounded-full px-3 py-1.5 font-mono text-[12px] transition-colors ${
                active === k ? "bg-ink text-white" : "bg-vellum text-graphite hover:text-ink"
              }`}
            >
              {k.replace("_", " ")}
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-8 hairline overflow-hidden rounded-2xl bg-white">
        <table className="w-full text-left">
          <thead className="text-[12px] uppercase text-slate">
            <tr>
              <th className="px-5 py-2 font-normal">At</th>
              <th className="px-3 py-2 font-normal">Event</th>
              <th className="px-3 py-2 font-normal">Scene</th>
              <th className="px-3 py-2 font-normal">Task</th>
              <th className="px-3 py-2 font-normal">Path</th>
              <th className="px-5 py-2 font-normal">Digest or receipt</th>
            </tr>
          </thead>
          <tbody className="font-mono text-[12px]">
            {rows.map((e, i) => (
              <tr key={`${e.scene}-${e.at}-${i}`} className="border-t border-gridline">
                <td className="px-5 py-2 text-slate">{stamp(e.at).slice(11, 19)}</td>
                <td className={`px-3 py-2 ${e.event === "verdict" ? (e.verdict === "REFUSED" ? "text-[var(--color-ember-text)]" : "text-ink") : "text-graphite"}`}>
                  {e.event}
                  {e.verdict ? ` · ${e.verdict.toLowerCase()}` : ""}
                </td>
                <td className="px-3 py-2 text-slate">{e.scene}</td>
                <td className="px-3 py-2 text-slate">{short(e.task, 10)}</td>
                <td className="px-3 py-2 text-slate">{e.path || ""}</td>
                <td className="px-5 py-2 text-slate">
                  {e.receipt
                    ? `receipt ${short(e.receipt, 16)}`
                    : e.digest
                      ? `digest ${short(e.digest, 16)}`
                      : (e.codes || []).join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-[12px] text-slate">
        showing {rows.length} of {store.totals.events}
      </p>
    </div>
  );
}
