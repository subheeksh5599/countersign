# Submission text — paste-ready

Everything below is written to be pasted into the submission form as-is. Links are
live. The video is recorded separately from `VIDEO.md`.

## Name

Countersign

## One-line pitch

Bob's own rollback can undo what Bob changed. Countersign stops Bob changing code
using facts reality already invalidated.

## Short description (form field, ~300 chars)

Countersign is a pre-action gate for Bob. Before any state-changing tool call it
compares the evidence the task is holding — file digests, command results, the
committed revision — against the workspace, and refuses the call with exit code 2
when the evidence no longer describes the repository. Verdict is arithmetic, not
opinion, and every refusal carries a receipt.

## Long description

IBM's own documentation says it plainly: compaction is lossy, information can remain
in the context window, and Bob keeps treating plausible text as fact on later prompts
("Bob does not reliably ignore plausible text just because it is wrong"). The
documented recovery is that a human notices and starts a new task. Rollback does not
close the gap either — it is task-scoped, and changes made outside a task are not
included.

So the failure state is routine: a task reads a file, something else changes that file
— a second task, a colleague, a background process — and the task edits using facts
that are no longer true. Today the answer is "a human should notice".

Countersign turns that into a runtime boundary. It uses Bob's own lifecycle hooks:

- SessionStart opens an evidence manifest for the task.
- PostToolUse records a SHA-256 digest of every file read, with provenance, and every
  command result.
- PreToolUse recomputes the digests and refuses the proposed action when the evidence
  a task holds is no longer evidence for the workspace.

The refusal is exit code 2 — Bob's own blocking hook — names the digest the task
holds and the digest on disk, states the recovery, and writes a SHA-256 receipt. The
verdict is a digest comparison: no model call, no tokens, ~300 ms, inside the 10 s
default hook timeout.

Refusal codes: `EVIDENCE_SUPERSEDED`, `CROSS_TASK_EVIDENCE`, `REVISION_MOVED`,
`COMMAND_RESULT_CHANGED`, `UNSUPPORTED_SUBTASK_EVIDENCE`, `UNVERIFIED_TARGET`,
`OUTSIDE_WORKSPACE`, `NO_MANIFEST`. The gate fails closed: unreadable payload, a
payload that is not an object, or an unresolvable workspace all refuse.

## Why Bob is load-bearing, not decorative

Delete Bob and the product does not exist. Countersign consumes the artifact only the
runtime can emit — the hook payload carrying `session_id`, `tool_name`, `tool_input`,
`cwd` — and enforces at the runtime's own blocking point, `PreToolUse` with exit code
2. There is no other way to refuse a tool call before it runs. The receipt carries the
same `session_id` the runtime prints as its Task ID, so a refusal joins to the
runtime's own task record. Nothing here calls a private API; the gate works because
Bob documents and enforces its hooks.

## Live links

- Repository: https://github.com/subheeksh5599/countersign
- Evidence page from the live session: https://subheeksh5599.github.io/countersign/
- The comparison page: https://subheeksh5599.github.io/countersign/comparison.html
- The scripted two-task scene: https://subheeksh5599.github.io/countersign/scripted.html
- Raw record behind the page: https://github.com/subheeksh5599/countersign/tree/master/docs/evidence-store

## Business value

Bob is metered. Generation costs Bobcoins, and the cost lands whether or not the work
survives review. When a task edits on invalidated facts, the cost of the task is
spent and the repair is spent again: someone re-reads the file, re-runs the commands,
reviews a diff that should never have been produced, and often reverts a change that
looked plausible in every test that ran before the edit. That is the budget line this
product protects — wasted generation plus rework — and it is the one Bob's own
analytics will not see. Bobalytics reports adoption, the Bob factor and Bobcoin spend;
nothing in it describes what happened to the workspace after the tokens were spent.

The buyer is whoever pays for Bob seats and owns the review burden: the engineering
manager or platform lead adopting the runtime across a team. The deployment shape is
the one the product already has — a machine-wide hook block that resolves the
workspace from the payload, so every repository in the organisation refuses by default
without per-project setup. Adoption is measurable from the evidence store: counted
refusals, counted recoveries, and per-task exports that can be attached to a review.

This is a control, not a new instrument. It does not claim a new market; it claims a
measurable saving on an existing one, and it is honest about the tension: IBM sells
Bobcoins, so the savings case has to be made on adoption and renewals (teams ship
changes that survive review, so they keep the seats) rather than on tokens not burned.

## Originality

The object under verification is not the agent's judgement, it is the identity of the
evidence. Every project in this field audits what the agent *said* or *produced*:
reviews, tests, evidence packs, model checkers. Countersign asks a different question
at a different place — at the boundary, before the action: is the evidence this task
is holding still the evidence for this repository?

That question is not new elsewhere; it is concurrency control. Databases, version
control and build systems have enforced it for decades. What is new here is applying
it to an agent's own context, where the "stale copy" is not a cached page but a
conversation that keeps treating a file as it was, and where the enforcement point is
the tool call itself. The mechanism is borrowed on purpose; the boundary is not
occupied.

## What is not proven — stated in the same breath as the win

- The runtime's own edit path was observed applying an edit to a file that had changed
  since the task read it (the diff's search block still matched), but one observation
  is not a specification. Treat "the runtime does not check evidence identity" as
  observed behaviour, not a documented guarantee.
- Command-result handling is covered by tests and the scripted scene, but no live
  session's command payload has been captured yet.
- Subtask attribution is enforced by the gate's own contract, not by an observed
  payload field: the payloads captured so far carry no subtask id.
- A competent agent often refreshes its evidence before writing, and then the gate
  admits. That is correct behaviour, not a gap; the gate exists for the moment a task
  acts on evidence it did not refresh. Staging that moment uses a labelled harness
  that writes the path inside the read -> write window.
- Enforcement is local to the machine running the runtime. Someone who controls that
  machine can remove the hook. Organisation-wide enforcement is the runtime's own
  enforced-hooks mechanism, and the exported receipts are the piece a CI job would
  check server-side; that CI check is roadmap, not shipped.
- The evidence store is a file: tamper-evident only if you commit the event log or
  export records outside the workspace. It is not signed by a third party.

## Verification a judge can run

```sh
git clone https://github.com/subheeksh5599/countersign && cd countersign
python3 tests/test_gate.py      # 15 behaviour cases
python3 tests/test_matrix.py    # 500 cases
sh install.sh --global          # machine-wide gate, CLI, hook block
```

Then run one task, change the file it read, and attempt the edit: the refusal, the
exit code, the receipt and the diff are all visible.
