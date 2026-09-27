# Limits, stated deliberately

What this gate does not do, in the same breath as what it does.

- The runtime's own edit path was observed to apply an edit to a file that had changed
  since the task read it: the diff's search block still matched the line it targeted,
  the unrelated change was not a conflict, and the write landed. It does not refuse on
  the evidence identity, so this case belongs to the gate. Its tool documentation
  describes no such check, and one observation is not a specification — treat the
  claim as observed behaviour, not as a documented guarantee. The cross-task, revision, command-result and subtask cases are the ones
  this gate provably owns, and they are covered by tests.
- A competent agent often refreshes its evidence before writing, and then the gate
  admits. That is correct behaviour, not a gap: the gate exists for the moment when
  a task acts on evidence it did not refresh. Staging that moment on demand is a
  concurrency problem, not a coding problem; the live demonstration uses a labelled
  harness that writes the path inside the read -> write window.
- Subtask attribution requires the payload to identify the subtask. The payloads
  observed so far do not carry a subtask id, so per-subtask manifests are separated
  by the gate's own contract, not by an observed field.
- Command results are compared by digest of the recorded result text. A command whose
  output changes for benign reasons (timestamps, durations) will register as a
  contradiction. Treat that as a fact to resolve, not a bug to silence.
- Revisions are read with `git rev-parse HEAD:<path>`. Workspaces that are not git
  repositories fall back to digest comparison alone.
- Command payloads were not exercised in the captured live session: the payloads on
  record come from `glob`, `read_file` and `apply_diff`. Command-result handling is
  covered by tests and by the demo scene, not yet by a captured live payload.
- Nothing here reads a private API. The gate consumes the public hook payload and the
  workspace itself.

## Installed twice

Both a machine-wide block and a workspace block observe the same call. The live session
on 2026-09-27 shows the effect plainly: 4 intercepted calls, 8 verdict events and only 4
receipt files, because the machine-wide copy was still the older build, which appended a
verdict to the event log without writing a receipt. With one gate installed the counts are
exactly equal: 3 intercepted calls, 3 verdict events, 3 receipt files, every hash verifying,
each receipt chained to the one before it.

Install one or the other. `install.sh` now prints a warning when it finds a machine-wide
block while merging a workspace block, because two gates means every state-changing call is
checked twice and produces two receipts.

## Two clones, two manifests

A change that exists only on another machine is invisible to a local check. The multi
developer scene shows the boundary: the edit is admitted before the fetch and refused after
it.

What closes part of the gap is shipped. `countersign replay` takes the receipts and the
repository and re-derives every verdict from the inputs the receipt itself recorded, so a
machine that never ran the gate can check that a verdict was reached rather than typed.
`.github/workflows/replay.yml` runs it on every push and then forges a verdict and asserts
the replay fails. What that does not do is stop an edit on a machine with no hook: the
replay audits verdicts, it does not enforce across machines. See `docs/CI.md`.
