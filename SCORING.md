# Countersign — what each judging axis needs, and where it comes from

Four axes, equal weight. This file maps each axis to the artifact that satisfies it
and states the honest expectation, so effort goes where the marks are.

## Application of technology — target 5
Needs: the framework visibly doing the work, live, in a real deployment.
Satisfied by:
- Enforcement on the runtime's own tool boundary, refusing with exit code 2, driven
  by its SessionStart, PostToolUse and PreToolUse hooks (`hooks.json`).
- Evidence taken from the runtime's own task records: session identity, workspace
  commit, tool payloads (`.countersign/tasks/`, `.countersign/events.jsonl`).
- The gate itself: 15 end-to-end tests over real git workspaces (`tests/test_gate.py`).
- Measured cost of a decision: 308 ms with 200 recorded observations, against a
  10 s default hook timeout — so refusal is cheap enough to run on every call.
- 15 behaviour cases and a 500-case matrix, all passing (`tests/`).
Wiring into a licensed install is done: machine-wide gate, CLI and global hook block,
idempotent. Live payload field names were confirmed from a real session (`probe`
mode); captured copies are in `tests/fixtures/real_payloads.json`.

## Presentation — target 5
Needs: a short video with problem, solution, value, market, revenue, roadmap and
competitive analysis.
Satisfied by: `VIDEO.md`, a timed shot list covering all seven, built around the
refusal scene and the recovery. `lens.py` produces the one page the video is
recorded over, rendered from real events (4 tasks, 3 observations, 4 refusals,
1 admission in the current demo run).
Still outstanding: recording it inside the installed runtime.

## Business value — target 4.5
Needs: a new market or industry disruption, stated with a buyer.
Satisfied by: buyer (platform and developer-productivity teams running agents on
shared repositories, plus the risk owners who authorise autonomy), budget line
(change governance and controls), measured saving (stale-evidence edits refused,
incidents avoided, rework not done), and the revenue path (per repository, an
enterprise policy package, organisation-wide enforcement, exportable evidence
records).
Honest ceiling: it is a control, not a new instrument. The truthful claim is a new
required control for autonomous edits, not a new market, and 4.5 is what that is
worth on this rubric.

## Originality — target 4.5
Needs: a new perspective, not a better implementation.
Satisfied by: the object is evidence identity, not an opinion. Comparable work in
this event audits judgement — risk classification, explanation honesty,
documentation drift — and every one of those needs a model to decide. This decides
with digests, task identity and commit identity, and it refuses at the boundary.
The subtask refusal (`UNSUPPORTED_SUBTASK_EVIDENCE`) covers the handoff case in the
same mechanism.
Honest ceiling: concurrency control exists as prior art in databases and build
systems, so this is a known mechanism applied at a boundary nobody has applied it
to, which is worth 4.5 rather than 5.

## Where the remaining effort goes, in order
1. Wire the hooks and record the refusal live (unlocks Application and Presentation).
2. Determine whether the runtime's own edit path already refuses a changed file — if
   it does, the headline scene becomes the cross-task case and the pitch barely moves.
3. Record the video from the lens page.
4. Publish the repository and serve the lens page from a URL.
5. Keep the "what is not proven" list visible in the submission.
