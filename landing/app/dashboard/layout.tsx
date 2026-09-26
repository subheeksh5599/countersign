import SideNav from "./SideNav";
import { store, stamp } from "@/lib/store";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const note = `${store.totals.scenes} scenes, ${store.totals.events} events`;
  return (
    <div className="flex min-h-screen bg-white">
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 border-r border-gridline md:block">
        <SideNav note={note} />
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-gridline bg-white/95 px-6 backdrop-blur">
          <div className="flex items-center gap-3 md:hidden">
            <span className="font-medium">Countersign</span>
          </div>
          <div className="flex items-center gap-5 text-body text-graphite md:hidden">
            <a href="/dashboard" className="hover:text-ink">
              Overview
            </a>
            <a href="/dashboard/refusals" className="hover:text-ink">
              Refusals
            </a>
            <a href="/dashboard/tasks" className="hover:text-ink">
              Tasks
            </a>
            <a href="/dashboard/events" className="hover:text-ink">
              Event log
            </a>
          </div>
          <span className="font-mono text-[12px] text-slate">synced {stamp(store.generated_at).slice(0, 10)}</span>
        </header>
        <main className="px-6 py-8">{children}</main>
      </div>
    </div>
  );
}
