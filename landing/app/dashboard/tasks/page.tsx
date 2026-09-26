import { store, short, stamp } from "@/lib/store";

export const metadata = { title: "Tasks · Countersign" };

export default function Tasks() {
  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-heading-lg font-medium tracking-[-0.2px]">Tasks</h1>
      <p className="mt-2 text-body text-slate">
        One manifest per task: the commit it opened on, every path it observed, and what it was relying on.
      </p>

      <div className="mt-8 space-y-4">
        {store.tasks.map((task) => (
          <article key={`${task.scene}-${task.task}`} className="hairline rounded-2xl bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gridline px-5 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <p className="font-mono text-[13px]">{task.task}</p>
                <span className="rounded-full bg-vellum px-2 py-0.5 font-mono text-[11px] text-graphite">
                  {task.scene}
                </span>
                {task.implicit ? (
                  <span className="rounded-full bg-vellum px-2 py-0.5 font-mono text-[11px] text-graphite">
                    implicit
                  </span>
                ) : null}
              </div>
              <p className="font-mono text-[12px] text-slate">commit {short(task.commit)}</p>
            </div>
            <div className="grid gap-x-8 gap-y-3 px-5 py-4 text-body sm:grid-cols-4">
              <div>
                <p className="text-slate">Opened</p>
                <p className="font-mono text-[12px]">{stamp(task.opened_at).slice(0, 19)}</p>
              </div>
              <div>
                <p className="text-slate">Observations</p>
                <p className="font-mono text-[12px]">{task.observations.length}</p>
              </div>
              <div>
                <p className="text-slate">Commands recorded</p>
                <p className="font-mono text-[12px]">{task.commands}</p>
              </div>
              <div>
                <p className="text-slate">Contradictions</p>
                <p className="font-mono text-[12px]">
                  <span className={task.contradictions ? "text-[var(--color-ember-text)]" : ""}>{task.contradictions}</span>
                </p>
              </div>
            </div>
            {task.observations.length ? (
              <table className="w-full border-t border-gridline text-left">
                <thead className="text-[12px] uppercase text-slate">
                  <tr>
                    <th className="px-5 py-2 font-normal">Path</th>
                    <th className="px-3 py-2 font-normal">Digest</th>
                    <th className="px-3 py-2 font-normal">Via</th>
                    <th className="px-5 py-2 font-normal">Observed</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-[13px]">
                  {task.observations.slice(0, 12).map((o) => (
                    <tr key={`${task.task}-${o.path}`} className="border-t border-gridline">
                      <td className="px-5 py-2">{o.path}</td>
                      <td className="px-3 py-2 text-slate">{short(o.digest, 16)}</td>
                      <td className="px-3 py-2 text-slate">{o.via}</td>
                      <td className="px-5 py-2 text-slate">{stamp(o.at).slice(11, 19)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
            {task.observations.length > 12 ? (
              <p className="border-t border-gridline px-5 py-2 font-mono text-[12px] text-slate">
                {task.observations.length - 12} further observations in the manifest
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}
