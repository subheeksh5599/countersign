# Countersign — completion checklist

Legend: [x] done and verified by a real run · [ ] outstanding · (axis) the judging
axis it moves · → the artifact that proves it.

## A. Mechanism — done
- [x] Evidence manifest per task, not one global file (a second task must not wipe
      the first task's evidence) (Application) → `.countersign/tasks/<task>.json`
- [x] Digest recorded on every file read, with provenance (direct / named subtask)
- [x] Command results recorded; a result that changes underneath the task is
      detected (Application) → `COMMAND_RESULT_CHANGED`
- [x] Refusal with exit code 2 at the tool boundary, fail-closed with no manifest
- [x] Refusal names held digest, on-disk digest, reason, recovery steps
- [x] SHA-256 receipt per verdict appended to an event log (Presentation, Business)
- [x] Subtask claim with no observation behind it refused (Originality) →
      `UNSUPPORTED_SUBTASK_EVIDENCE`
- [x] Policy knob to refuse writes to never-observed paths (Business) →
      `COUNTERSIGN_REQUIRE_PRIOR_READ=1`
- [x] `probe` mode: records raw payloads without ever blocking, so live field names
      are learned from a real session rather than assumed (Application)
- [x] `export` mode: one hashed evidence record per task, for review (Business)
- [x] Decision cost measured: 122 ms against 200 observations, well inside the 10 s
      default hook timeout (Application)

## B. Proof surface — done
- [x] 15 end-to-end tests over real git workspaces and real subprocesses
- [x] Two-task scene reproduced on a real public repository with a real external
      change → `demo.sh`
- [x] Command scene reproduced → `demo2.sh`
- [x] One page rendering the real record: counts, refusal cards with receipts, what
      each task holds, who observed what, full event log → `lens.py`, `site/index.html`
- [x] README with the vendor's quotes, wiring schema, transcripts, measured cost and
      an explicit "what is not proven" section
- [x] Submission packet with all five axes → `PITCH.md`
- [x] Five-minute video plan with timings mapped to the judged elements → `VIDEO.md`
- [x] Axis-by-axis scoring map with honest ceilings → `SCORING.md`

## C. Outstanding — needs the licensed install
- [ ] Merge the hook block into a real workspace (Application) → `install.sh --write`,
      then confirm the hook is listed as active
- [ ] Run `probe` for one real session and read the payloads: tool name spellings,
      whether reads carry a subtask id, whether command output is present
      (Application)
- [ ] Determine whether the runtime's own edit path already refuses a write to a file
      that changed since it was read (Originality) → if it does, lead with the
      cross-task and command cases
- [ ] Confirm the 10 s timeout is sufficient in practice (measured 122 ms locally)
- [ ] Run the two-task scene live, with the refusal visible on screen (Presentation)
- [ ] Confirm task/session records are reachable for the receipt join (Business)
- [ ] Organisation-wide block: `hooks-global.json` with the gate path substituted, so
      every workspace refuses by default (Business)

## D. Submission surface
- [x] Static evidence page prepared and deployable → `site/index.html`
- [x] Video plan, pitch packet and scoring map written
- [ ] Publish the repository (public, clean history, live-status line at the top)
- [ ] Record the five-minute video using `VIDEO.md`
- [ ] Serve `site/index.html` from a URL and link it in the submission
- [ ] One-screen comparison: what the field audits (judgement) versus what this
      audits (identity)
- [ ] Business paragraph in the submission itself, not only in the repo
- [ ] Publish the not-proven list in the submission, in the same breath as the win

## E. Optional, if time remains
- [x] Second refusal scene: a destructive command refused while a recorded result is
      contradicted → `demo2.sh`
- [x] Provenance visible per observation in the lens ("who observed what")
- [x] Export mode producing a hashed record per task
- [ ] Multi-developer demo: two workspaces sharing one repository
- [ ] A third refusal scene: workspace commit moving mid-task

## F. Scoring map — where the marks come from
- Application: a live refusal produced by the runtime's own hook mechanism on a real
  repository, plus the public repo. → sections A, B, C.
- Presentation: the refusal, the recovery, and one lens page built from real events.
  → sections B, C, D.
- Business: buyer, budget line, measured saving, organisation-wide enforcement.
  → `PITCH.md` market section, items in C and D.
- Originality: the object is evidence identity, not opinion; the field audits
  judgement. → `PITCH.md` competitive position, lens page, subtask refusal.
