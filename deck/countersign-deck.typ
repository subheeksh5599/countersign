// Countersign — project deck. 16:9, one slide per page.
//
// Build (13 slides):
//   woff2_decompress geist.woff2 && woff2_decompress geist-mono.woff2   # from demo/intro/assets
//   typst compile --font-path fonts countersign-deck.typ countersign-deck.pdf
//
// Verify: pages must equal slides (typst pushes an overflowing slide onto a
// second page silently), and every slide title must appear on its own page.
// Colours are the product's own tokens: ember, vellum, gridline, ink.
#let ember = rgb("#ff4d00")
#let vellum = rgb("#f9f9f9")
#let gridline = rgb("#e5e7eb")
#let ink = rgb("#262626")
#let muted = rgb("#6b7280")
#let mono = "Geist Mono"

#set page(
  width: 33.867cm,
  height: 19.05cm,
  margin: (x: 2.1cm, y: 1.5cm),
  fill: vellum,
  footer: context [
    #set text(font: "Geist", size: 8pt, fill: muted)
    #line(length: 100%, stroke: 0.4pt + gridline)
    #v(0.25cm)
    #grid(
      columns: (1fr, auto),
      [Countersign],
      [#counter(page).display()],
    )
  ],
)

#set text(font: "Geist", size: 13pt, fill: ink)
#set par(leading: 0.72em, justify: false)
#show heading: it => block(above: 0pt, below: 0.5cm)[
  #text(size: 24pt, weight: "semibold", fill: ink)[#it.body]
  #v(0.18cm)
  #line(length: 3.2cm, stroke: 1.6pt + ember)
]

#let slide(body, brk: true) = {
  body
  if brk { pagebreak() }
}

#let lead = text.with(size: 15pt, fill: ink)
#let small = text.with(size: 11.5pt, fill: muted)
#let code(body) = block(
  inset: 0.45cm,
  radius: 0.12cm,
  fill: rgb("#f0f1f3"),
  stroke: 0.5pt + gridline,
  width: 100%,
)[
  #set text(font: mono, size: 10.5pt, fill: ink)
  #body
]
#let stat(val, label, note) = block(
  inset: 0.42cm,
  radius: 0.12cm,
  fill: white,
  stroke: 0.5pt + gridline,
  width: 100%,
)[
  #text(size: 23pt, weight: "semibold", fill: ember)[#val]
  #v(0.08cm)
  #text(size: 9pt, weight: "medium", fill: ink)[#label]
  #v(0.12cm)
  #text(size: 9pt, fill: muted)[#note]
]

// ---------------------------------------------------------------- 1 title
#grid(
  rows: (1fr, auto),
  [#v(2.6cm)
    #text(size: 54pt, weight: "semibold", tracking: -0.5pt)[Countersign]
    #v(0.5cm)
    #line(length: 4.2cm, stroke: 2.2pt + ember)
    #v(0.55cm)
    #text(size: 19pt)[A gate in front of every state-changing tool call a coding agent makes.]
    #v(0.9cm)
    #block(width: 24cm)[#text(size: 13pt, fill: muted)[
      It refuses the edit when the evidence the task is holding no longer describes the
      repository. The verdict is a hash comparison, and every verdict leaves a receipt.
    ]],
  ],
  [#text(size: 11pt, fill: muted)[Built for the IBM Bob 2.0 runtime]]
)
#pagebreak()

// ---------------------------------------------------------------- 2 problem
#slide[
  #heading[What I set out to prevent]
  #lead[
    An agent reads a file, decides what to change, and writes several minutes later. In those
    minutes a formatter rewrites the file, a second agent edits the same tree, or a pull moves
    the branch the path sat on.
  ]
  #v(0.5cm)
  #lead[
    The write then lands and the tool call reports success. Nothing raises an error, because the
    file exists, the diff applies cleanly, and nothing conflicted. The repository ends up holding
    an edit derived from text that was never true of it.
  ]
  #v(0.5cm)
  #lead[
    Existing tooling answers the easy question, whether the call succeeded. I wanted the harder
    one answered before the call runs: is the evidence this task holds still an accurate
    description of the repository it is about to change?
  ]
]

// ---------------------------------------------------------------- 3 why worse
#slide[
  #heading[Bob's own behaviour widens the gap]
  #small[After an edit, the runtime tells the agent this, captured from a live payload:]
  #v(0.35cm)
  #code["You do not need to re-read the file, as you have seen all changes.\nProceed with the task using these changes as the new baseline."]
  #v(0.5cm)
  #lead[
    The agent is told to treat a change as its new baseline, which is correct when nothing else
    moved and wrong when something did.
  ]
  #v(0.4cm)
  #lead[
    Bob's documentation is candid about the consequence: compaction is lossy, wrong context
    persists in the transcript, and the documented recovery is for a person to notice and start a
    new task. That leaves a human doing the job of a mechanism.
  ]
]

// ---------------------------------------------------------------- 4 the rule
#slide[
  #heading[The rule I built the whole thing around]
  #v(0.2cm)
  #block(
    inset: 0.6cm,
    radius: 0.12cm,
    fill: white,
    stroke: 1pt + ember,
    width: 100%,
  )[
    #text(size: 17pt)[No state-changing action may use repository evidence whose identity is no
      longer current.]
  ]
  #v(0.7cm)
  #lead[So the gate records, per task, what the task actually knew:]
  #v(0.35cm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.45cm,
    [*files it read* #linebreak() #small[the SHA-256 digest of the file at the moment it was read]],
    [*commands it ran* #linebreak() #small[the digest of the result text the runtime returned]],
    [*where the path sat* #linebreak() #small[the committed revision, resolved through git]],
  )
]

// ---------------------------------------------------------------- 5 decision
#slide[
  #heading[How it decides]
  #lead[I kept a model out of the decision path. The verdict is a SHA-256 comparison, so the same
    inputs always give the same answer.]
  #v(0.6cm)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.5cm,
    stat("exit 0", "ADMITTED", "the evidence a task holds still describes the repository"),
    stat("exit 2", "REFUSED", "the call does not run, and the refusal names which fact moved"),
  )
  #v(0.6cm)
  #lead[Eight reasons it can refuse, each with its own code:]
  #v(0.3cm)
  #small[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.5cm,
      row-gutter: 0.24cm,
      [`NO_MANIFEST` the task holds no manifest],
      [`REVISION_MOVED` committed at a different revision],
      [`OUTSIDE_WORKSPACE` the target is outside the workspace],
      [`CROSS_TASK_EVIDENCE` the record belongs to another task],
      [`UNVERIFIED_TARGET` the path was never read],
      [`UNSUPPORTED_SUBTASK_EVIDENCE` evidence from another subtask],
      [`EVIDENCE_SUPERSEDED` the file moved after the read],
      [`COMMAND_RESULT_CHANGED` a recorded command now contradicts],
    )
  ]
]

// ---------------------------------------------------------------- 6 refusal
#slide[
  #heading[What a refusal actually says]
  #v(0.15cm)
  #code[
    REFUSED: EVIDENCE_SUPERSEDED
    About to modify pricing.ts.
    Evidence this task holds: baa5252515ea.
    Digest on disk now: f24af5254d22.
    \ \ EVIDENCE_SUPERSEDED: baa5252515ea -> f24af5254d22 (the file changed after this task observed it)
    \ \ REVISION_MOVED: a512df3add44 -> 2522bc69c806 (this path was committed at a different revision after the task observed it)
    Required recovery:
    \ \ 1. open a fresh task
    \ \ 2. re-observe pricing.ts
    \ \ 3. rerun the affected commands
    \ \ 4. record the new evidence manifest
    Refusal receipt: 582b05e62d75bb15b36dcc508822961aea3895dac43a3dfffbd203af87d4454e
    The action did not happen.
  ]
  #v(0.45cm)
  #small[Both digests are printed, so the refusal is checkable rather than a matter of trust. The
    agent gets the four steps that clear it.]
]

// ---------------------------------------------------------------- 7 receipts
#slide[
  #heading[Every verdict leaves a receipt]
  #lead[A verdict you cannot check afterwards is an assertion. So each decision writes a receipt
    holding the inputs it used, both digests, the code, the reason and the time it took.]
  #v(0.55cm)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.5cm,
    stat("chained", "TAMPER-EVIDENT BY ARITHMETIC", "each receipt stores the hash of the one before it, so the log is walkable"),
    stat("replay", "RE-DERIVED, NOT TRUSTED", "countersign replay recomputes every verdict from the inputs its own receipt recorded"),
  )
  #v(0.55cm)
  #lead[
    A machine that never ran the gate can still check that a verdict was reached rather than typed.
    On every push, the CI workflow replays a committed store and then forges a verdict to prove the
    replay has teeth.
  ]
]

// ---------------------------------------------------------------- 8 wiring
#slide[
  #heading[How I wired it into Bob]
  #lead[Bob exposes lifecycle hooks, and the gate is driven by three of them.]
  #v(0.5cm)
  #grid(
    columns: (auto, auto, 1fr),
    row-gutter: 0.35cm,
    column-gutter: 0.7cm,
    [#text(font: mono, size: 11pt)[SessionStart]], [#text(font: mono, size: 11pt)[session-start]], [opens the evidence manifest for the task],
    [#text(font: mono, size: 11pt)[PostToolUse]], [#text(font: mono, size: 11pt)[record]], [digests every file read and every command result],
    [#text(font: mono, size: 11pt)[PreToolUse]], [#text(font: mono, size: 11pt)[check]], [admits or refuses the proposed state-changing call],
  )
  #v(0.6cm)
  #lead[
    The block goes into `.bob/settings.json` for one workspace or `~/.bob/settings/settings.json`
    machine-wide, using Bob's documented schema. One installer merges it and resolves the workspace
    from the `cwd` field that every payload carries, so there is no per-project configuration.
  ]
]

// ---------------------------------------------------------------- 9 real run
#slide[
  #heading[One real Bob task, with the gate installed]
  #v(0.2cm)
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    gutter: 0.4cm,
    stat("1.05", "BOBCOINS SPENT", "a real task, not a rehearsal"),
    stat("44.6s", "WALL TIME", "eight tool calls"),
    stat("4", "ATTEMPTS REFUSED", "across two edit tools"),
    stat("0", "BYTES CHANGED", "the file was left untouched"),
  )
  #v(0.65cm)
  #small[Task `eea2941f4db4a1f67c401695b74446d0`. The agent read the file, then tried the edit four
    times. Every attempt came back exit 2 with `EVIDENCE_SUPERSEDED` and wrote its own receipt,
    chained to the one before it.]
  #v(0.45cm)
  #lead[The agent's own closing report, unprompted:]
  #v(0.25cm)
  #code["The safety guard correctly blocked the edit... I need to re-read the current state before modifying it."]
]

// ---------------------------------------------------------------- 10 console
#slide[
  #heading[The console reads the runtime, never a snapshot]
  #lead[Five pages, each its own URL, and every panel is filled by the store the gate itself
    wrote. There is no bundled sample data.]
  #v(0.5cm)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.5cm,
    [*protect* #linebreak() #small[connect a repository, install the hook, run one turn and watch the verdict]],
    [*evidence* #linebreak() #small[what each session held, and how many calls it lost]],
    [*interceptor* #linebreak() #small[every call with its class, verdict, exit code and latency]],
    [*receipts* #linebreak() #small[the chain, and a replay that recomputes each verdict]],
  )
  #v(0.55cm)
  #small[With the runtime down, each page says disconnected and prints the exact command to start
    it, rather than quietly rendering a wrong-shaped fallback. The button that runs an agent turn
    spawns Bob headlessly and reports the exit code Bob really returned.]
]

// ---------------------------------------------------------------- 11 cost
#slide[
  #heading[What it costs, because a gate that slows the agent down gets uninstalled]
  #v(0.3cm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.45cm,
    stat("308 ms", "ONE DECISION", "against a manifest holding 200 observations"),
    stat("10 s", "THE HOOK TIMEOUT", "Bob's default budget for a pre-tool hook"),
    stat("~30x", "HEADROOM", "measured over 20 runs on a two-core laptop"),
  )
  #v(0.7cm)
  #lead[
    Reading the manifest and measuring the workspace is the whole cost. Nothing is called over the
    network and nothing is inferred, so the number does not move with repository size the way a
    model call would.
  ]
]

// ---------------------------------------------------------------- 12 limits
#slide[
  #heading[What it does not claim]
  #v(0.35cm)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.6cm,
    row-gutter: 0.4cm,
    [*Not a content check.* #small[The pending diff reaches the hook and the gate ignores it on
      purpose. A wrong or hostile edit to a file that has not moved is admitted. This enforces
      whether the facts are current, not whether the change is good.]],
    [*Enforcement is per machine.* #small[The hook stops the edit where it is installed. What
      travels between machines is the receipt, which the replay can check.]],
    [*A fetch it never saw is invisible.* #small[A local gate cannot compare against a branch that
      was never fetched. One recorded run shows the write admitted before the fetch and refused
      after it.]],
    [*The store is chained, not signed.* #small[Hash chaining makes edits detectable and the
      replay makes verdicts re-derivable. Neither is a signature.]],
  )
  #v(0.5cm)
  #small[Organisation-wide enforcement as the default is not built, and a repository guarded on one
    machine is not guarded on another unless the hook is installed there too.]
]

// ---------------------------------------------------------------- 13 close
#slide(brk: false)[
  #heading[Where to look]
  #v(0.4cm)
  #grid(
    columns: (auto, 1fr),
    row-gutter: 0.42cm,
    column-gutter: 1cm,
    [*Repository*], [public, and linked in the submission form],
    [*Demo video*], [youtu.be/NQ43DN8eA8I],
    [*Product site*], [countersign-eight.vercel.app],
  )
  #v(0.8cm)
  #lead[
    The repository carries the gate, the local runtime, the console, the hook blocks and the
    captured payloads from a real session. 531 tests pass in three suites, the acceptance run
    drives 21 steps against a live runtime, and the CI workflow that replays committed stores is
    green.
  ]
  #v(0.5cm)
  #text(size: 13pt, fill: ember)[Everything on these slides comes from a recorded run, not from a
    plan.]
]
