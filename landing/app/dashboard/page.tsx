import Link from "next/link";
import { store, short, stamp } from "@/lib/store";

export const metadata = { title: "Overview · Countersign" };

function Stat({ value, label, hint }: { value: string | number; label: string; hint?: string }) {
  return (
    <div className="hairline rounded-2xl bg-white p-6">
      <p className="text-heading font-medium tracking-[-0.2px]">{value}</p>
      <p className="mt-1 text-body text-graphite">{label}</p>
      {hint ? <p className="mt-3 font-mono text-[12px] text-slate">{hint}</p> : null}
    </div>
  );
}

export default function Overview() {
  const t = store.totals;
  const refused = store.verdicts.filter((v) => v.verdict === "REFUSED");
  const share = t.verdicts ? Math.round((t.refusals / t.verdicts) * 100) : 0;

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-heading-lg font-medium tracking-[-0.2px]">Overview</h1>
          <p className="mt-2 text-body text-slate">
            Every verdict below came from a gate that ran. The store is committed in the repository.
          </p>
        </div>
        <p className="font-mono text-[12px] text-slate">
          {stamp(t.first_at)} → {stamp(t.last_at)}
        </p>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={t.tasks} label="tasks tracked" hint={`${t.scenes} recorded scenes`} />
        <Stat value={t.observations} label="observations recorded" hint="file reads, digested" />
        <Stat value={t.refusals} label="refused actions" hint={`${share}% of verdicts`} />
        <Stat value={t.admissions} label="admitted actions" hint="evidence current" />
      </div>

      <section className="mt-10">
        <h2 className="text-heading-sm font-medium">Verdict split</h2>
        <div className="mt-4 flex h-3 overflow-hidden rounded-full border border-gridline">
          <span
            className="bg-ember"
            style={{ width: `${share}%` }}
            aria-label={`${t.refusals} refusals`}
          />
          <span className="flex-1 bg-vellum" aria-label={`${t.admissions} admissions`} />
        </div>
        <div className="mt-3 flex gap-6 text-body text-slate">
          <span>
            <span className="font-mono text-ink">{t.refusals}</span> refused, action did not run
          </span>
          <span>
            <span className="font-mono text-ink">{t.admissions}</span> admitted, receipt written
          </span>
        </div>
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="hairline overflow-hidden rounded-2xl bg-white">
          <div className="flex items-center justify-between border-b border-gridline px-5 py-3">
            <h2 className="text-body font-medium">Recorded scenes</h2>
            <Link href="/dashboard/events" className="text-body text-graphite hover:text-ink">
              Event log
            </Link>
          </div>
          <table className="w-full text-left">
            <thead className="text-[12px] uppercase text-slate">
              <tr>
                <th className="px-5 py-2 font-normal">Scene</th>
                <th className="px-3 py-2 font-normal">Tasks</th>
                <th className="px-3 py-2 font-normal">Events</th>
                <th className="px-3 py-2 font-normal">Refused</th>
                <th className="px-5 py-2 font-normal">Admitted</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[13px]">
              {store.scenes.map((s) => (
                <tr key={s.name} className="border-t border-gridline">
                  <td className="px-5 py-2.5">{s.name}</td>
                  <td className="px-3 py-2.5 text-slate">{s.tasks}</td>
                  <td className="px-3 py-2.5 text-slate">{s.events}</td>
                  <td className="px-3 py-2.5">
                    <span className={s.refusals ? "text-[var(--color-ember-text)]" : "text-slate"}>{s.refusals}</span>
                  </td>
                  <td className="px-5 py-2.5 text-slate">{s.admissions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="hairline overflow-hidden rounded-2xl bg-white">
          <div className="flex items-center justify-between border-b border-gridline px-5 py-3">
            <h2 className="text-body font-medium">Latest refusals</h2>
            <Link href="/dashboard/refusals" className="text-body text-graphite hover:text-ink">
              All refusals
            </Link>
          </div>
          <ul>
            {refused.slice(0, 6).map((v) => (
              <li key={`${v.task}-${v.path}-${v.at}`} className="border-t border-gridline px-5 py-3">
                <p className="font-mono text-[12px] text-[var(--color-ember-text)]">{v.codes?.[0] || "REFUSED"}</p>
                <p className="mt-1 text-body">{v.path || "command"}</p>
                <p className="mt-1 font-mono text-[12px] text-slate">
                  {v.scene} · {short(v.task, 10)} · {stamp(v.at).slice(11, 19)}
                </p>
              </li>
            ))}
            {refused.length === 0 ? (
              <li className="px-5 py-4 text-body text-slate">No refusal recorded in this store.</li>
            ) : null}
          </ul>
        </div>
      </section>
    </div>
  );
}
