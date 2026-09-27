"use client";

import { useEffect } from "react";

const REPO = "https://github.com/subheeksh5599/countersign";
const EVIDENCE = "https://subheeksh5599.github.io/countersign/";
const COMPARISON = "https://subheeksh5599.github.io/countersign/comparison.html";

const SCENE = [
  { step: "The task reads pricing.ts", detail: "its evidence is recorded", state: "recorded" },
  { step: "A second task writes the file", detail: "the file no longer matches", state: "drift" },
  { step: "The task proposes its edit", detail: "refused, exit code 2", state: "refused" },
];

const CARDS = [
  {
    title: "Evidence identity",
    body: "Every file a task reads is stored as a digest. The digest is compared with the file at the moment of the action.",
    icon: (
      <path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6l7-3z" />
    ),
  },
  {
    title: "Arithmetic verdicts",
    body: "Digests, task identity and the committed revision decide the outcome. No model sits in the decision path.",
    icon: (
      <>
        <path d="M4 19h16" />
        <path d="M4 15l4-5 4 3 4-7 4 5" />
      </>
    ),
  },
  {
    title: "Recorded refusals",
    body: "Each verdict is written with a SHA-256 receipt and the same task id the runtime reports for the session.",
    icon: (
      <>
        <path d="M6 3h9l4 4v14H6z" />
        <path d="M9 12h7M9 16h4" />
      </>
    ),
  },
];

export default function Page() {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      nodes.forEach((n) => n.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 }
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-gridline bg-white/95 backdrop-blur">
        <div className="shell flex h-16 items-center justify-between">
          <a href="#top" className="text-[15px] font-medium tracking-tight">
            Countersign
          </a>
          <nav className="hidden items-center gap-6 md:flex">
            {[
              ["Boundary", "#boundary"],
              ["Difference", "#difference"],
              ["Scene", "#scene"],
              ["Verify the record", "/record"],
            ].map(([label, href]) => (
              <a key={label} href={href} className="text-body text-graphite transition-colors hover:text-ink">
                {label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <a href="/console" className="ghost hidden px-3 py-2 text-body font-medium sm:block">
              Console
            </a>
            <a href="/record" className="cta px-4 py-2 text-body font-medium">
              Verify the record
            </a>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="relative overflow-hidden border-b border-gridline">
          <div className="dot-field pointer-events-none absolute inset-0 opacity-70" aria-hidden />
          <div className="shell relative py-24 text-center md:py-36">
            <h1 className="reveal in mx-auto max-w-4xl max-w-4xl text-[40px] font-medium leading-[1.07] tracking-[-0.26px] md:text-display-xl md:leading-[1] md:tracking-[-0.6px]">
              Refuse the edit when the <span className="text-ember">evidence has moved</span>
            </h1>
            <p className="reveal in mx-auto mt-7 max-w-2xl text-body-lg text-graphite">
              Countersign compares the evidence a task is holding with the repository before every
              state-changing call. If the file, the command results or the committed revision have
              moved, the call does not run.
            </p>

            <div className="reveal in mt-14 flex items-center justify-center gap-3 text-body">
              <a href={REPO} className="cta px-5 py-2.5 font-medium">
                Read the source
              </a>
              <a
                href="/record"
                className="hairline ghost flex items-center gap-1.5 px-4 py-2.5 font-medium text-graphite"
              >
                Verify the record
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h13M13 6l6 6-6 6" />
                </svg>
              </a>
              <a
                href="/console"
                className="hairline ghost flex items-center gap-1.5 px-4 py-2.5 font-medium text-graphite"
              >
                Open the console
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h13M13 6l6 6-6 6" />
                </svg>
              </a>
            </div>
          </div>
        </section>

        <section id="boundary" className="border-b border-gridline">
          <div className="shell py-28 md:py-36">
            <div data-reveal className="reveal max-w-2xl">
              <span className="flex items-center gap-2 font-mono text-[12px] uppercase text-slate" style={{ letterSpacing: "0.12em" }}>
                <span className="inline-block h-1 w-1 rounded-full bg-ember" />
                Boundary
              </span>
              <h2 className="mt-4 text-heading-lg font-medium tracking-[-0.2px] md:text-display md:leading-[1.07]">
                Three guarantees, all enforced before the call runs
              </h2>
            </div>
            <div className="mt-16 grid gap-8 md:grid-cols-3">
              {CARDS.map((c, i) => (
                <article
                  key={c.title}
                  data-reveal
                  className="card reveal p-8 text-center"
                  style={{ transitionDelay: `${i * 90}ms` }}
                >
                  <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-gridline bg-white">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff4d00" strokeWidth="1.6" strokeLinecap="round">
                      {c.icon}
                    </svg>
                  </span>
                  <h3 className="mt-5 text-body-lg font-medium">{c.title}</h3>
                  <p className="mt-2 text-body text-slate">{c.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="difference" className="border-b border-gridline bg-vellum">
          <div className="shell py-28 md:py-36">
            <div data-reveal className="reveal mx-auto max-w-2xl text-center">
              <span className="flex items-center justify-center gap-2 font-mono text-[12px] uppercase text-slate" style={{ letterSpacing: "0.12em" }}>
                <span className="inline-block h-1 w-1 rounded-full bg-ember" />
                Difference
              </span>
              <h2 className="mt-4 text-heading-lg font-medium tracking-[-0.2px] md:text-display md:leading-[1.07]">
                Before the action, not after the review
              </h2>
            </div>
            <div className="mx-auto mt-16 grid max-w-4xl gap-8 md:grid-cols-2">
              <div data-reveal className="reveal card bg-white p-8">
                <p className="font-mono text-[12px] uppercase text-slate" style={{ letterSpacing: "0.12em" }}>
                  The field
                </p>
                <p className="mt-3 text-heading-sm font-medium">Did the agent make a mistake?</p>
                <ul className="mt-5 space-y-2 text-body text-slate">
                  <li>read the diff, read the transcript</li>
                  <li>ask a model whether the change looks wrong</li>
                  <li>run the test suite afterwards</li>
                  <li>have a reviewer judge the result</li>
                </ul>
                <p className="mt-6 border-t border-gridline pt-4 text-body text-slate">
                  An opinion, formed after the action, unable to produce a copy of what the task read.
                </p>
              </div>
              <div data-reveal className="reveal card bg-white p-8" style={{ transitionDelay: "90ms" }}>
                <p className="font-mono text-[12px] uppercase text-[var(--color-ember-text)]" style={{ letterSpacing: "0.12em" }}>
                  Countersign
                </p>
                <p className="mt-3 text-heading-sm font-medium">Is this evidence still evidence?</p>
                <ul className="mt-5 space-y-2 text-body text-slate">
                  <li>the digest recorded when the file was read</li>
                  <li>the digest on disk at the moment of the action</li>
                  <li>the committed revision for that path</li>
                  <li>the command results the task relies on</li>
                </ul>
                <p className="mt-6 border-t border-gridline pt-4 text-body text-ink">
                  Arithmetic, evaluated at the boundary, refused with exit code 2 and a receipt.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="scene" className="border-b border-gridline">
          <div className="shell py-28 md:py-36">
            <div data-reveal className="reveal max-w-2xl">
              <span className="flex items-center gap-2 font-mono text-[12px] uppercase text-slate" style={{ letterSpacing: "0.12em" }}>
                <span className="inline-block h-1 w-1 rounded-full bg-ember" />
                Scene
              </span>
              <h2 className="mt-4 text-heading-lg font-medium tracking-[-0.2px] md:text-display md:leading-[1.07]">
                Two tasks, one file
              </h2>
              <p className="mt-4 text-body-lg text-graphite">
                The failure this gate exists for, taken from a recorded session.
              </p>
            </div>
            <div className="mt-16 grid gap-8 md:grid-cols-3">
              {SCENE.map((s, i) => (
                <div
                  key={s.step}
                  data-reveal
                  className="reveal card bg-white p-6"
                  style={{ transitionDelay: `${i * 110}ms` }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[12px] text-slate">{`0${i + 1}`}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 font-mono text-[11px] uppercase ${
                        s.state === "refused" ? "bg-ember text-white" : "bg-vellum text-graphite"
                      }`}
                      style={{ letterSpacing: "0.08em" }}
                    >
                      {s.state}
                    </span>
                  </div>
                  <p className="mt-5 text-body-lg font-medium">{s.step}</p>
                  <p className="mt-2 font-mono text-[13px] text-slate">{s.detail}</p>
                </div>
              ))}
            </div>
            <div data-reveal className="reveal mt-8 overflow-hidden rounded-full border border-gridline bg-white">
              <div className="flex h-1 w-[200%]">
                <span className="tick block h-full w-1/2 bg-[linear-gradient(90deg,transparent,#e5e7eb_35%,#ff4d00_50%,#e5e7eb_65%,transparent)]" />
                <span className="tick block h-full w-1/2 bg-[linear-gradient(90deg,transparent,#e5e7eb_35%,#ff4d00_50%,#e5e7eb_65%,transparent)]" />
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-gridline bg-vellum">
          <div className="shell grid gap-8 py-24 md:grid-cols-3">
            {[
              ["8", "refusal codes, each named"],
              ["308 ms", "per decision, measured over 20 runs"],
              ["0", "model calls in the decision path"],
            ].map(([n, label], i) => (
              <div key={label} data-reveal className="reveal text-center" style={{ transitionDelay: `${i * 80}ms` }}>
                <p className="text-heading-lg font-medium tracking-[-0.2px] md:text-display">{n}</p>
                <p className="mt-2 text-body text-slate">{label}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-b border-gridline">
          <div className="shell py-28 text-center md:py-36">
            <h2 data-reveal className="reveal mx-auto max-w-3xl text-heading-lg font-medium tracking-[-0.2px] md:text-display md:leading-[1.07]">
              Give every task the same boundary
            </h2>
            <p data-reveal className="reveal mx-auto mt-5 max-w-xl text-body-lg text-graphite">
              Install the gate machine wide, or read the source first.
            </p>
            <div data-reveal className="reveal mt-9 flex items-center justify-center gap-3">
              <a href={REPO} className="cta px-5 py-2.5 font-medium">
                Read the source
              </a>
              <a href={EVIDENCE} className="ghost px-4 py-2.5 font-medium text-graphite">
                Live evidence page
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-white">
        <div className="shell flex flex-col items-center justify-between gap-6 py-12 text-body text-slate md:flex-row">
          <span className="font-medium text-ink">Countersign</span>
          <div className="flex items-center gap-6">
            <a href={REPO} className="hover:text-ink">
              Source
            </a>
            <a href="/record" className="hover:text-ink">
              Verify the record
            </a>
            <a href={EVIDENCE} className="hover:text-ink">
              Evidence
            </a>
            <a href="/console" className="hover:text-ink">
              Console
            </a>
            <a href={COMPARISON} className="hover:text-ink">
              Comparison
            </a>
          </div>
          <span className="font-mono text-[12px] text-slate">Runs on the PreToolUse hook</span>
        </div>
      </footer>
    </>
  );
}
