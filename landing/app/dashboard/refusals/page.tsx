import { store, short, stamp, DECLARED_CODES } from "@/lib/store";

export const metadata = { title: "Refusals · Countersign" };

export default function Refusals() {
  const refused = store.verdicts.filter((v) => v.verdict === "REFUSED");
  const observed = Object.entries(store.codes).sort((a, b) => b[1] - a[1]);
  const notObserved = DECLARED_CODES.filter((c) => !store.codes[c]);
  const max = observed.length ? observed[0][1] : 1;

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-heading-lg font-medium tracking-[-0.2px]">Refusals</h1>
      <p className="mt-2 text-body text-slate">
        Each entry is a state-changing call that did not run, with the code, the target and the receipt.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-3">
          {refused.map((v) => (
            <article key={`${v.scene}-${v.task}-${v.path}-${v.at}`} className="hairline rounded-2xl bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-mono text-[13px] text-[var(--color-ember-text)]">{v.codes?.join(" + ") || "REFUSED"}</p>
                <p className="font-mono text-[12px] text-slate">{stamp(v.at)}</p>
              </div>
              <dl className="mt-4 grid gap-x-8 gap-y-2 text-body sm:grid-cols-2">
                <div>
                  <dt className="text-slate">Target</dt>
                  <dd className="font-mono text-[13px]">{v.path || "command"}</dd>
                </div>
                <div>
                  <dt className="text-slate">Task</dt>
                  <dd className="font-mono text-[13px]">{v.task}</dd>
                </div>
                <div>
                  <dt className="text-slate">Scene</dt>
                  <dd className="font-mono text-[13px]">{v.scene}</dd>
                </div>
                <div>
                  <dt className="text-slate">Evidence held</dt>
                  <dd className="font-mono text-[13px]">{short(v.evidence_digest, 32)}</dd>
                </div>
              </dl>
              <p className="mt-4 break-all font-mono text-[11px] text-slate">receipt {v.receipt}</p>
            </article>
          ))}
          {refused.length === 0 ? (
            <p className="hairline rounded-2xl bg-white p-5 text-body text-slate">
              No refusal recorded in this store.
            </p>
          ) : null}
        </div>

        <div className="hairline h-fit rounded-2xl bg-white p-5">
          <h2 className="text-body font-medium">Codes exercised</h2>
          <ul className="mt-4 space-y-3">
            {observed.map(([code, count]) => (
              <li key={code}>
                <div className="flex items-center justify-between font-mono text-[12px]">
                  <span>{code}</span>
                  <span className="text-slate">{count}</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-vellum">
                  <span className="block h-full bg-ember" style={{ width: `${(count / max) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-6 border-t border-gridline pt-4">
            <p className="font-mono text-[11px] uppercase text-slate" style={{ letterSpacing: "0.1em" }}>
              Declared, not yet exercised
            </p>
            <p className="mt-2 font-mono text-[12px] leading-relaxed text-slate">
              {notObserved.join(", ")}
            </p>
            <p className="mt-3 text-body text-slate">
              These codes are covered by the test suite. None has appeared in a recorded session yet, so
              the dashboard does not count them.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
