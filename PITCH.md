# Countersign — submission packet

## 10-second hook
The agent's own documentation admits it: compaction is lossy, and wrong facts stay
in the transcript and keep being treated as true. Countersign refuses the edit when
the evidence behind it no longer describes the repository.

## One line
Obligations of reality, enforced before the write: no state-changing action may use
evidence whose identity is no longer current.

## Problem
A task reads a file, plans a change, and works for a long time. Meanwhile another
task, another developer, or a background process changes that file — or the commit
moves, or a command that was recorded produces a different result. The transcript
still holds the old facts. The edit lands anyway, built on a version of the
repository that no longer exists, and tests often pass because nothing checks the
external contract.

Quoted from the runtime's own documentation: "Compaction is lossy. Details from
early in the task may not survive." — "Bob does not reliably ignore plausible text
just because it is wrong." — "The reliable fix is a new task." That fix is manual,
and it depends on a person noticing. Rollback does not cover it either: "external
changes: modifications made outside of tasks are not included."

## Solution
A gate on the tool boundary, driven by the runtime's lifecycle hooks.

- `SessionStart` opens an evidence manifest for the task.
- `PostToolUse` records the digest of every file read and every command result,
  with provenance (direct or a named subtask).
- `PreToolUse` verifies before a state-changing call and returns exit code 2 to
  refuse when evidence is stale, foreign to this task, or unsupported.

No model participates in the verdict. Digests, task identity and commit identity
decide it. Every verdict writes a SHA-256 receipt and an event line.

Refusal codes: `EVIDENCE_SUPERSEDED`, `CROSS_TASK_EVIDENCE`, `WORKSPACE_MOVED`,
`COMMAND_RESULT_CHANGED`, `UNSUPPORTED_SUBTASK_EVIDENCE`, `UNVERIFIED_TARGET`,
`NO_MANIFEST`.

## Value
- Stops edits built on facts that reality already invalidated, which is exactly the
  failure mode the runtime documents and cannot currently detect.
- Makes parallel agent work safe: a second task touching the same files is no
  longer invisible to the first.
- Produces an evidence record per task for the people who are not the agent's user
  — a reviewer, an incident responder, a client, an acquirer.
- Costs nothing per decision: the check is a digest comparison, not a model call,
  so it scales with the number of actions rather than with token spend.

## Market and revenue
Buyer: platform and developer-productivity teams running autonomous coding agents
on shared repositories, and the risk owners who authorise that autonomy.

Budget line: controls and change governance, the same budget that pays for
review gates, policy engines and audit tooling today.

Revenue: per-repository enforcement, an enterprise policy package (organisation-wide
enforcement via the runtime's enforced-hook mechanism), and a reviewable evidence
record for audits.

Measured value: stale-evidence edits refused, incidents avoided, and downstream
rework that does not happen.

## Competitive position
The field audits judgement; this audits identity. Comparable projects in this event
classify risk, check whether an explanation is honest, or audit documentation drift
— all of which require an opinion about behaviour. Countersign asks a question with
an arithmetic answer: does the evidence the task is holding still describe this
workspace. Nothing in the adjacent space answers that, and the prior art in
databases and build systems is concurrency control, not an agent boundary.

## Roadmap
1. Hooks installed per workspace and per machine, the two-task scene recorded, the
   demo filmed and published. (done; nothing here has run inside a licensed
   desktop install, which is the one install path not exercised)
2. Subagent evidence separated per subtask, with the parent refusing claims that
   have no observation behind them. (implemented; payload shape to confirm)
3. Organisational enforcement: the hook block shipped as a policy, so every
   developer's workspace refuses stale evidence by default.
4. Evidence records as an exportable artifact: one hashed page per task for review
   and incident postmortems. (built: `countersign export`, rendered by `lens.py`)
5. Extend the same gate to other state-changing surfaces the runtime exposes,
   including commands with external effects.

## Demo script (2 minutes)
1. State the constraint. Task A reads a file.
2. Task B — a second task on the same repository — changes that file. Show the real
   change on disk.
3. Task A returns and proposes its edit. The write is refused, exit code 2, with
   both digests, the reason, and the recovery steps.
4. Ask the obvious question on camera: could we just have an agent check? An agent
   can say what changed; nothing can produce the copy of what was read. Show the
   refusal naming the digest it held.
5. Task A opens fresh, re-observes, and the same edit is admitted with a receipt.
6. Open the lens page: refusals, manifests, and the full event log from real runs.

## What is not proven (published deliberately)
- Whether the runtime's own edit path already refuses a write to a changed file.
  Its tool documentation describes no such behaviour; silence is not evidence. The
  cross-task, workspace-move, contradicted-command and subtask cases are the ones
  this gate provably owns.
- Subagent provenance requires the hook payload to identify the subtask.
- Everything is verified on real git workspaces; no licensed install has been
  exercised yet.
