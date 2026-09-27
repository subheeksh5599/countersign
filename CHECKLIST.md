# Countersign — completion checklist

Legend: [x] done and verified by a real run · [~] built but not yet exercised end to
end · [ ] outstanding · (axis) the judging axis it moves · → the artifact that proves it.

Status line: public at github.com/subheeksh5599/countersign, pages published on GitHub
Pages, 531 tests passing (15 behaviour cases + 500-case matrix + 16 receipt, chain,
redaction, policy and replay cases), the 21 step fresh machine acceptance run passing against a
live runtime, one live refusal and one live admission recorded from a real session, two
further scenes recorded verbatim, and a local control plane (runtime plus a five page
console that holds no sample data) driving the same gate command the agent's hook runs.

## A. Mechanism — done and verified
- [x] Evidence manifest per task, not one global file (Application) →
      `.countersign/tasks/<task>.json`
- [x] A resumed task keeps the evidence it already holds — the manifest is no longer
      reopened and erased. This was a real defect found by the matrix suite and fixed
- [x] Digest recorded on every file read, with provenance (direct / named subtask)
- [x] Revisions compared per path (`git rev-parse HEAD:<path>`), so an unrelated
      commit no longer blocks and a commit touching the edited path does →
      `REVISION_MOVED`
- [x] Command results recorded; a result that changes underneath the task is detected
      → `COMMAND_RESULT_CHANGED`
- [x] Refusal with exit code 2 at the tool boundary, fail-closed with no manifest
- [x] Fail-closed parsing: unreadable payload, payload that is not an object, and an
      unresolvable workspace all refuse rather than crash or permit. A valid-JSON
      non-object payload used to crash the gate with exit 1; fixed
- [x] Refusal names the held digest, the on-disk digest, the reason and the recovery
- [x] SHA-256 receipt per verdict appended to an event log (Presentation, Business)
- [x] Subtask claim with no observation behind it refused (Originality) →
      `UNSUPPORTED_SUBTASK_EVIDENCE`
- [x] Policy knob to refuse writes to never-observed paths (Business) →
      `COUNTERSIGN_REQUIRE_PRIOR_READ=1`
- [x] `probe` mode: records raw payloads without ever blocking (Application)
- [x] `export` mode: one hashed evidence record per task, for review (Business)
- [x] Decision cost measured for real: 308 ms against 200 recorded observations, mean
      of 20 runs on a two-core laptop, 30x inside the 10 s default hook timeout
- [x] Installer idempotent: a second install adds 0 hook entries. Duplicate entries
      (gate running twice per call) were a real defect found and fixed

## B. Proof surface — done
- [x] 15 end-to-end behaviour cases over real git workspaces and real subprocesses
- [x] 500-case matrix derived from the documented decision order, all passing; it
      found the three defects listed in section A
- [x] Two-task scene reproduced on a real public repository with a real external
      change → `demo.sh`
- [x] Command scene reproduced → `demo2.sh`
- [x] One page rendering the real record: counts, refusal cards with receipts, what
      each task holds, who observed what, full event log → `lens.py`, `site/index.html`
- [x] README with the vendor's quotes, wiring schema, transcripts, measured cost and
      an explicit "what is not proven" section
- [x] Submission packet with all five axes → `PITCH.md`
- [x] Five-minute video plan with timings mapped to the judged elements → `VIDEO.md`
- [x] Axis-by-axis scoring map with honest ceilings → `SCORING.md`,
      `docs/SCORING_RATIONALE.md`
- [x] Limits stated in the same breath as the win → `docs/LIMITS.md`

## C. Live integration — done, was "needs the licensed install"
- [x] Gate installed machine-wide: `/home/arch/.local/share/countersign/countersign.py`,
      CLI at `~/.local/bin/countersign`, global hook block in `~/.bob/settings/settings.json`
- [x] Workspace block merged into a real workspace and confirmed active
- [x] `probe` run against a real session: payloads captured and read. Tool name
      spellings confirmed (`glob`, `read_file`, `apply_diff`); reads carry
      `tool_response`; no subtask id in any payload. Copies in
      `tests/fixtures/real_payloads.json`
- [x] Payload `session_id` equals the task id the runtime prints ("Task ID"), so a
      receipt joins to the runtime's own task record
- [x] 10 s hook timeout confirmed sufficient in practice (measured 308 ms)
- [x] Two-task scene run live, refusal visible, receipt recorded → `docs/LIVE_RUN.md`
- [x] Organisation-wide block installed with the workspace resolved from the payload
      `cwd`, so no per-project configuration is needed
- [x] The runtime's own edit path does not refuse on evidence identity: an edit was
      observed applying to a file that had changed since the read, because the diff's
      search block still matched. Observed behaviour, recorded in `docs/LIMITS.md`

## D. Submission surface
- [x] Repository published — public, real commits, live-status block at the top
- [x] Evidence page published from `docs/` on GitHub Pages, linked from
      `SUBMISSION.md`; raw record committed under `docs/evidence-store/`
- [x] One-screen comparison built → `docs/comparison.html` (field audits judgement,
      this audits identity), plus the paragraph in `SUBMISSION.md`
- [x] Business paragraph written for the form itself, including the honesty line about
      IBM selling Bobcoins → `SUBMISSION.md` market section
- [x] Not-proven list written for the form itself, in the same breath as the win →
      `SUBMISSION.md`, mirrored in `docs/LIMITS.md`
- [x] Paste-ready submission text for every form field → `SUBMISSION.md`

## E. Optional
- [x] Second refusal scene: a destructive command refused while a recorded result is
      contradicted → `demo2.sh`
- [x] Provenance visible per observation in the lens ("who observed what")
- [x] Export mode producing a hashed record per task
- [x] Multi-developer demo run for real: two clones, a bare remote, one refusal
      before the fetch and one after → `scripts/demo_multi_developer.sh`,
      verbatim in `docs/MULTI_DEV_RUN.md`
- [x] Third scene run for real: byte-identical file, moved revision, refused
      `REVISION_MOVED` → `scripts/scene_revision_moved.sh`, verbatim in
      `docs/SCENE_REVISION_MOVED.md`
- [x] Evidence store from the live session committed for verification →
      `docs/evidence-store/`

## F. Control plane — the runtime and the console
- [x] Runtime on 127.0.0.1:4319, stdlib only, serving HTTP and server sent events, and
      holding no evidence of its own → `runtime/countersign_runtime.py`, `docs/RUNTIME.md`
- [x] Watcher with three real jobs: forward gate events, re-hash held files and publish
      `filesystem_changed` when one moves, publish `git_head_changed` when HEAD moves
- [x] Console with five pages and a sidebar, each item on its own URL, no sample data:
      protect, evidence, interceptor, receipts, self-test → `landing/app/console/`
- [x] Homepage answers the five questions: protected?, what is held?, what went stale?,
      what did the last call do?, can the mechanism be reproduced right now?
- [x] Receipts persisted as full field files, chained by `previous_receipt_hash`, with a
      local verify that recomputes the hash → `.countersign/receipts/`
- [x] Secret redaction verified by test: an API key, an authorization header and a
      password leave no trace in the receipt file, structure preserved
- [x] Explicit state-changing policy, recorded in each receipt, failing closed for an
      unrecognised tool or command → `tests/test_receipts.py`
- [x] Real recovery: refresh re-hashes the held files and rewrites the manifest, and the
      retried call is then admitted with a second receipt
- [x] the console can drive one real agent turn itself: a bundled deterministic reference
      agent, or the vendor CLI when its key is in the runtime environment, with a second
      real process writing the file inside the window (verified from the browser: exit 2,
      receipt written, file left as the other process wrote it)
- [x] staleness persisted as a record with a time on it (`.countersign/stale.jsonl`),
      not recomputed per request
- [x] every manifest in the store is listed and can be inspected, not only the newest
- [x] `countersign replay` recomputes every stored verdict from the inputs the receipt
      itself recorded; a forged verdict fails it (16/16 in `tests/test_receipts.py`)
- [x] the same replay runs in CI on a clone, with a forgery asserted to fail
      (`.github/workflows/replay.yml`, `docs/evidence-store/ci-bundle/`)
- [x] 21 step acceptance run against a live runtime, on a repository it creates from
      nothing → `scripts/acceptance.py`
- [x] One command startup → `run.sh`
- [x] Static snapshot console retired: the product console reads the runtime, and reports
      DISCONNECTED with the start command rather than showing plausible data

## G. Where the marks come from
- Application: refusal produced by the runtime's own hook on a real session, from its
  own payloads, with its own task id in the receipt; a local control plane over the real
  store; public repo; 531 tests and a 21 step acceptance run.
  → sections A, B, C, F.
- Presentation: the refusal, the recovery, the receipt chain and a console built from
  live state only. → sections B, C, F, and the open item in D.
- Business: buyer, budget line, measured saving, machine-wide enforcement by default.
  → `PITCH.md` market section, section C.
- Originality: the object is evidence identity, not opinion; the field audits
  judgement. → `PITCH.md` competitive position, lens page, subtask refusal.
