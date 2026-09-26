"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/refusals", label: "Refusals" },
  { href: "/dashboard/tasks", label: "Tasks" },
  { href: "/dashboard/events", label: "Event log" },
];

export default function SideNav({ note }: { note: string }) {
  const pathname = usePathname();
  return (
    <nav className="flex h-full flex-col gap-8 p-6">
      <Link href="/" className="text-[15px] font-medium tracking-tight">
        Countersign
      </Link>
      <div className="flex flex-1 flex-col gap-1">
        {ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-body transition-colors ${
                active ? "bg-vellum font-medium text-ink" : "text-graphite hover:bg-vellum"
              }`}
            >
              <span
                className={`inline-block h-3.5 w-[2px] rounded-full ${active ? "bg-ember" : "bg-transparent"}`}
                aria-hidden
              />
              {item.label}
            </Link>
          );
        })}
      </div>
      <div className="border-t border-gridline pt-4">
        <p className="font-mono text-[11px] uppercase text-slate" style={{ letterSpacing: "0.1em" }}>
          Store
        </p>
        <p className="mt-1 font-mono text-[12px] text-slate">{note}</p>
      </div>
    </nav>
  );
}
