"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useApi } from "@/lib/runtime";

const NAV = [
  { href: "/console", label: "protect" },
  { href: "/console/evidence", label: "evidence" },
  { href: "/console/interceptor", label: "interceptor" },
  { href: "/console/receipts", label: "receipts" },
  { href: "/console/self-test", label: "self-test" },
];

type Status = {
  protected?: boolean;
  repository?: string | null;
  branch?: string | null;
  hook_scope?: { installed?: boolean; scope?: string | null };
  runtime?: { version?: string; port?: number; uptime_s?: number };
  receipt_count?: number;
  stale?: number;
  disconnected?: boolean;
};

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const p = usePathname();
  const { data, error } = useApi<Status>("/api/status");
  const live = !!data && !error;
  const protectedNow = !!data?.protected;

  return (
    <div className="min-h-screen bg-vellum">
      <div className="mx-auto flex max-w-[1440px]">
        <aside className="sticky top-0 hidden h-screen w-[212px] shrink-0 flex-col border-r border-gridline bg-white px-3 py-4 md:flex">
          <Link href="/" className="px-2 font-mono text-[13px] tracking-[-0.1px] text-ink">
            countersign
          </Link>
          <div className="mt-1 px-2 font-mono text-caption uppercase tracking-[0.14em] text-slate">
            control plane
          </div>
          <nav className="mt-6 flex flex-col gap-[2px]">
            {NAV.map((n) => {
              const active = p === n.href;
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  className={`rounded-[6px] px-2 py-[7px] font-mono text-[12.5px] tracking-[0.02em] ${
                    active ? "bg-vellum text-ink" : "text-graphite hover:bg-vellum"
                  }`}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto space-y-2 border-t border-gridline pt-3 font-mono text-[11px] text-slate">
            <div className="flex items-center gap-2 px-1">
              <span
                className={`inline-block h-[7px] w-[7px] rounded-full ${
                  live ? "bg-emerald-500" : "bg-ember"
                }`}
              />
              <span className="uppercase tracking-[0.14em]">
                {live ? (protectedNow ? "protected" : "runtime up") : "disconnected"}
              </span>
            </div>
            <div className="truncate px-1" title={data?.repository || ""}>
              {data?.repository ? data.repository.split("/").slice(-2).join("/") : "no repository"}
            </div>
            <div className="px-1">
              {live
                ? `v${data?.runtime?.version} :${data?.runtime?.port} | ${data?.receipt_count ?? 0} receipts`
                : "runtime offline"}
            </div>
            <div className="px-1">
              hook: {data?.hook_scope?.scope || "not installed"}
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-4 py-4 md:px-6 md:py-5">
          <div className="mb-3 flex items-center gap-3 md:hidden">
            <Link href="/" className="font-mono text-[12.5px] text-ink">
              countersign
            </Link>
            <nav className="flex flex-wrap gap-2">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="rounded-pill border border-gridline bg-white px-2 py-[3px] font-mono text-[11px] text-graphite"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
