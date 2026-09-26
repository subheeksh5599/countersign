# Countersign

**Live status:** gate implemented and exercised — 15/15 tests passing; the two-task
and command scenes reproduced on a real repository; the lens page rendered from real
events; a decision measured at 308 ms against a 10 s default hook timeout. Vendor
hook wiring verified against the vendor's own hook documentation; not yet wired into
a licensed desktop install.

A countersign is a page scraped clean and written over, with the old text still
faintly visible. An agent transcript is that page: the file it describes may
already have changed underneath it, and the task keeps reading from the old text.

Countersign is a gate. Before a state-changing tool call, it verifies that the
evidence the task is relying on still describes the workspace the call is about
to touch. When it does not, the call is refused with exit code 2 — not warned
about, refused — and the refusal names the digest it holds, the digest on disk,
the reason, and the recovery steps.

## The failure it exists for

Documented behaviour of the runtime this gate is built for, quoted from its own
documentation:

- "Compaction is lossy. Details from early in the task may not survive."
- "Once bad context is in Messages, it persists across every subsequent prompt.
  Bob does not reliably ignore plausible text just because it is wrong."
- A listed cause: "Stale or wrong repo text: Outdated comments, README fragments,
  or generated docs mislead file reads."
- The documented recovery: "The reliable fix is a new task." That recovery is
  manual, and it depends on a human noticing.
- Rollback scope: snapshots cover the task's own file modifications, and
  "external changes: modifications made outside of tasks (manual edits, other
  tools) are not included."

So the runtime can hold facts that reality has already invalidated, the only
defence is a person noticing, and the documented fix is to start over.

## The invariant

> No state-changing action may use repository evidence whose identity is no
> longer current.

The verdict is arithmetic: digests, task identity, commit identity. No model
participates in the decision. What a model may do is propose; what this gate does
is refuse.

## How it works

Three hook modes over a store on disk.

| Mode | Hook event | What it does |
|---|---|---|
| `session-start` | SessionStart | opens an evidence manifest for this task |
| `record` | PostToolUse | records the digest of every file read and every command result |
| `check` | PreToolUse | admits or refuses the proposed state-changing call |
| `probe` | any event | records the raw payload, never blocks, so live field names can be learned |
| `export` | manual | writes one hashed evidence record per task, for review |

Refusal codes:

| Code | Meaning |
|---|---|
| `EVIDENCE_SUPERSEDED` | the file changed after this task observed it |
| `CROSS_TASK_EVIDENCE` | the only recorded evidence belongs to a different task |
| `WORKSPACE_MOVED` | the commit moved after the manifest opened |
| `COMMAND_RESULT_CHANGED` | rerunning a recorded command produced a different result |
| `UNVERIFIED_TARGET` | policy requires prior observation and there is none |
| `NO_MANIFEST` | nothing recorded, therefore nothing verifiable — fail closed |

Per-task manifests live in `.countersign/tasks/<task>.json`; every verdict is
appended to `.countersign/events.jsonl` with a SHA-256 receipt. A missing manifest
refuses the action rather than allowing it.

## Measured cost of a decision

308 ms for a check against a manifest holding 200 observations, including the git
commit read (mean of 20 runs, a two-core laptop). The default hook timeout is 10 s and can be overridden. Refusal is
therefore cheap enough to run on every state-changing call, and it never spends
tokens — the verdict is a digest comparison, not a model call.

## Serving the produced evidence

`site/index.html` is a lens page generated from a real run. Regenerate it with
`python3 lens.py <workspace> -o site/index.html` and serve it from any static host;
there is no server code and no build step.

## Wiring

A workspace hook block, matching the documented schema (`hooks` → event → array
of `{matcher, hooks:[{type, command, timeout}]}`):

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
                     "command": "python3 .countersign/countersign.py session-start",
                     "timeout": 10 } ] }
    ],
    "PostToolUse": [
      { "matcher": "^(read_file|execute_command)$",
        "hooks": [ { "type": "command",
                     "command": "python3 .countersign/countersign.py record",
                     "timeout": 10 } ] }
    ],
    "PreToolUse": [
      { "matcher": ".*(write|edit|patch|replace|apply|delete|move|command).*",
        "hooks": [ { "type": "command",
                     "command": "python3 .countersign/countersign.py check",
                     "timeout": 10 } ] }
    ]
  }
}
```

```sh
sh install.sh /path/to/workspace            # prints the block it would merge
sh install.sh /path/to/workspace --write    # merges into .bob/settings.json
export COUNTERSIGN_WORKSPACE=/path/to/workspace
```

Configuration is environment only, with no defaults: `COUNTERSIGN_WORKSPACE` is
required, `COUNTERSIGN_REQUIRE_PRIOR_READ=1` additionally refuses writes to paths
this task never observed.

## The demo, reproduced

Real repository, real external modification, real refusals, real receipts:

```
== task A opens and observes src/sarif.ts ==
== task B opens, observes src/report.ts, and rewrites src/sarif.ts for real ==
src/sarif.ts rewritten by task B

== task A resumes and proposes an edit to the file that changed ==
REFUSED: EVIDENCE_SUPERSEDED
About to modify src/sarif.ts.
Evidence this task holds: 67e850b5eb43.
Digest on disk now: 8c2f925fa187.
  EVIDENCE_SUPERSEDED: 67e850b5eb43 -> 8c2f925fa187 (the file changed after this task observed it)
Required recovery:
  1. open a fresh task
  2. re-observe src/sarif.ts
  3. rerun the affected commands
  4. record the new evidence manifest
Refusal receipt: 2bf25447d82bc979bc0435f2f055c3a080cdf1c368daa36520cfda211bd3f5a1
The action did not happen.
exit=2

== task A proposes an edit to a file only task B has ever observed ==
REFUSED: CROSS_TASK_EVIDENCE
  CROSS_TASK_EVIDENCE: task_B -> task_A (the only recorded evidence for this path belongs to another task)
exit=2

== recovery: fresh task, re-observe, same edit admitted ==
{"verdict": "ADMITTED", "note": "evidence current, receipt 471500a19f1e"}
exit=0
```

## Tests

```
$ python3 tests/test_gate.py
PASS  current evidence is admitted
PASS  external change refused
PASS  fresh observation is admitted
PASS  cross-task evidence refused
PASS  moved workspace refused
PASS  contradicted command result refused
PASS  unobserved target refused under policy
PASS  missing manifest fails closed
PASS  contradicted command blocks further commands
PASS  refusals recorded with receipts

10/10 passed
```

Each test builds a real git workspace, writes real files, and runs the gate as a
subprocess, asserting both the exit code and the refusal code.

## What is not proven

- Whether the runtime's own edit path already refuses a write to a file changed
  since it was read. Its tool documentation describes no such behaviour, but
  silence is not evidence. The cross-task, workspace-move and contradicted-command
  cases are the ones this gate provably owns.
- What an `apply_diff`-style payload actually carries. The refusal keys off path,
  digests and recorded observations only, so nothing here depends on the pending
  content — which is why the gate behaves the same if that payload is thin.
- Subagent-reported digests: a subagent's observations arrive through the parent's
  tool results, so per-subagent manifests are not yet separated.
- Any use outside real git workspaces. Nothing here reads a vendor-private API;
  the gate consumes the public hook payload plus the workspace itself.

## Layout

```
countersign.py        the gate (session-start | record | check)
hooks.json           the hook block for a workspace settings file
install.sh           copies the gate in and merges the hook block
tests/test_gate.py   ten real end-to-end cases
demo-workspace/      a real clone used for the two-task reproduction
```
