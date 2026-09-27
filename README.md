# Countersign

**Live status:** gate, runtime and console implemented and exercised. 531 tests passing
(500 case matrix, 15 behaviour cases, 16 receipt, chain, redaction, policy and replay
cases), the 21 step fresh machine acceptance run passing against a live runtime, real refusals recorded from a
real agent session, receipts chained and verifiable, one decision measured at 308 ms
against a 200 observation manifest and a 10 s default hook timeout. Not yet wired into
a licensed desktop install.

A countersign is a page scraped clean and written over, with the old text still faintly
visible. An agent transcript is that page: the file it describes may already have changed
underneath it, and the task keeps reading from the old text.

Countersign is a local control plane for an AI coding agent. Before a state-changing tool
call it verifies that the evidence the task relies on still describes the repository the
call is about to touch. When it does not, the call is refused with exit code 2, not warned
about, and the refusal names the digest the task holds, the digest on disk, the reason and
the recovery steps. Every verdict persists a receipt.

```
agent --PreToolUse--> gate (countersign.py) --> .countersign/ store on disk
                                                     |
                                     runtime watches  +--> http://127.0.0.1:4319  (HTTP + SSE)
                                                     |
                                                             console  http://127.0.0.1:4311/console
```

The gate owns the state. The runtime owns no evidence of its own: every value it serves is
read from the store the gate wrote, or measured with real `git` and filesystem calls. The
console holds no sample data at all; when the runtime is not reachable it says so.

## The failure it exists for

Documented behaviour of the runtime this gate is built for, quoted from its own
documentation:

- "Compaction is lossy. Details from early in the task may not survive."
- "Once bad context is in Messages, it persists across every subsequent prompt. Bob does
  not reliably ignore plausible text just because it is wrong."
- A listed cause: "Stale or wrong repo text: Outdated comments, README fragments, or
  generated docs mislead file reads."
- The documented recovery: "The reliable fix is a new task." That recovery is manual, and
  it depends on a human noticing.
- Rollback scope: snapshots cover the task's own file modifications, and "external changes:
  modifications made outside of tasks (manual edits, other tools) are not included."

So the runtime can hold facts that reality has already invalidated, the only defence is a
person noticing, and the documented fix is to start over.

## The invariant

> No state-changing action may use repository evidence whose identity is no longer current.

The verdict is arithmetic: digests, task identity, commit identity. No model participates in
the decision path. A model may propose; this gate refuses.

## The gate

Six modes, each invoked by a hook event or by the operator, over a store on disk.

| Mode | Hook event | What it does |
|---|---|---|
| `session-start` | SessionStart | opens an evidence manifest for this task (resuming one keeps its evidence) |
| `record` | PostToolUse | records the digest of every file read and every command result |
| `check` | PreToolUse | admits, or refuses with exit 2, the proposed state-changing call |
| `refresh` | console | re-hashes the evidence this task holds and rewrites the manifest |
| `recheck` | console | the same decision as a dry run: writes no receipt and no event |
| `probe` | any event | records the raw payload, never blocks, so live field names can be learned |

Refusal codes:

| Code | Meaning |
|---|---|
| `EVIDENCE_SUPERSEDED` | the file changed after this task observed it |
| `CROSS_TASK_EVIDENCE` | the only recorded evidence for the path belongs to a different task |
| `COMMAND_RESULT_CHANGED` | rerunning a recorded command produced a different result |
| `UNSUPPORTED_SUBTASK_EVIDENCE` | a change was attributed to a subtask that never observed the path |
| `REVISION_MOVED` | the path was committed at a different revision after the task observed it |
| `UNVERIFIED_TARGET` | policy requires prior observation and there is none |
| `NO_MANIFEST` | nothing recorded, therefore nothing verifiable: fail closed |

Per-task manifests live in `.countersign/tasks/<task>.json`, the event log in
`.countersign/events.jsonl`, receipts in `.countersign/receipts/`. A missing manifest
refuses the action rather than allowing it. Anything unreadable, including a payload that
is valid JSON but not an object, fails closed.

## Receipts

Every verdict, allowed or refused, persists a receipt file with the full field set:

```
receipt_id, timestamp, session_id, repository, branch, git_head, tool_name,
tool_classification, classification_reason, tool_arguments, tool_arguments_hash,
affected_paths, evidence_hashes, current_hashes, verdict, reason_code, exit_code,
runtime_latency_ms, previous_receipt_hash, receipt_hash, seq
```

`receipt_hash` is the SHA-256 of the canonical receipt content, so verification is one
local recomputation: the console's verify button reads the stored file, strips
`receipt_hash`, hashes the rest and compares. `previous_receipt_hash` stores the hash of
the receipt written before it, which makes the log a chain: the console walks it and
reports whether every link verifies.

## Policy, secrets, classification

Tool calls are classified by an explicit policy, recorded in the receipt:

- file writes, edits, patches, deletes, moves and code generation are state-changing;
- git commit, checkout, reset, merge, rebase, package installs that touch lockfiles, in
  place edits and shell redirects are state-changing;
- read-only tools are read-only;
- for a shell call the command decides first: a mutation pattern makes it state-changing,
  an explicit read-only allowlist (`git status`, `git log`, `ls`, `grep`, `cat`,
  `git diff`, and similar) makes it read-only, and anything else fails closed;
- an unrecognised tool, or a payload with no tool name, fails closed.

Stored tool arguments are redacted: values whose key or shape looks like a credential are
replaced with a length and digest fingerprint, while the structure of the call is kept so a
reviewer can see which operation was intercepted and what it was aimed at. Verified by
test: a payload carrying an API key, an authorization header and a password leaves none of
the three anywhere in the receipt file.

## Measured cost of a decision

308 ms for a check against a manifest holding 200 observations, including the git commit
read (mean of 20 runs, a two core laptop). The default hook timeout is 10 s and can be
overridden. Refusal is therefore cheap enough to run on every state-changing call, and it
never spends tokens: the verdict is a digest comparison, not a model call.

## Run it

```sh
sh run.sh                      # runtime on 4319, console on 4311
sh run.sh --runtime-only       # runtime only
COUNTERSIGN_WORKSPACE=/path/to/repo sh run.sh
```

Then open `http://127.0.0.1:4311/console`. Nothing is installed globally and nothing is
sent anywhere: Python 3 and Node are the only requirements.

The console is five operational pages, each reading the live runtime over HTTP and
subscribing to its server sent event stream:

| Page | What it shows |
|---|---|
| `protect` | protection state, repository, branch, HEAD, session, last verdict, last receipt, live latency; **run one real agent turn** with a driver and an optional second writer; the staleness the watcher recorded, with the time it was first seen; held evidence against current repository; the real recovery action; latest intercepted call; latest receipt; security state; operator actions; run self-test |
| `evidence` | every manifest in the store, not only the newest, each inspectable; the selected session's evidence set with filters, per item held digest, current digest, git revision, last read, last verified, status, and per item re-check and refresh |
| `interceptor` | every intercepted call with classification, verdict, reason, exit code, latency and receipt; detail view with the redacted arguments and a replay of the deterministic check |
| `receipts` | the receipt log, the chain, a detail view with copy, download and verify, and **replay every stored verdict from its own recorded inputs** |
| `self-test` | the whole mechanism run against a fresh temporary repository, with the real exit codes, both receipts and the file content on disk afterwards |

Repository controls (connect, protect, stop, refresh git state, create demo repository,
start demo) and operator actions (start session, record read, attempt edit) all perform
real operations: they install or remove real hook entries, invoke the real gate command
with the payload the agent sends, and re-hash real files.

"Run agent turn" is the one to watch. It runs a real agent against the protected
repository: the bundled reference agent (`runtime/reference_agent.py`, deterministic, no
model and no key) or the vendor CLI when it is on this machine's PATH with its key in the
runtime's environment. With the second writer ticked, a real second process rewrites the
file inside the window between the agent's read and its attempt, so the call comes back
exit 2 with a receipt written and the file left exactly as the other process wrote it. The
driver that ran is named in the result; nothing is claimed about a driver that was not
available.

## The runtime API

`GET /api/status`, `/api/repo`, `/api/session`, `/api/sessions`, `/api/evidence`,
`/api/stale`, `/api/interceptor`, `/api/receipts`, `/api/receipts/<id>`,
`/api/receipts/<id>/download`, `/api/security`, `/api/stream` (SSE).
`POST /api/repo/connect`, `/api/repo/demo`, `/api/repo/protect`, `/api/repo/stop`,
`/api/repo/refresh`, `/api/session/start`, `/api/evidence/read`, `/api/evidence/refresh`,
`/api/evidence/recheck`, `/api/interceptor/attempt`, `/api/interceptor/replay`,
`/api/receipts/<id>/verify`, `/api/selftest`, `/api/demo/start`.

Event names on the stream: `runtime_hello`, `session_started`, `file_read`,
`evidence_created`, `filesystem_changed`, `git_head_changed`, `tool_intercepted`,
`evidence_checked`, `tool_refused`, `tool_allowed`, `receipt_created`,
`evidence_refreshed`, `repository_connected`, `protection_started`, `protection_stopped`,
`selftest_step`, `selftest_started`, `selftest_finished`, `check_replayed`. The watcher
polls nothing on a timer in the browser: pages subscribe and refetch when the runtime
publishes.

## Wiring

`install.sh` copies the gate into the workspace and merges the hook block. It is
idempotent: a second install adds no entries.

```sh
sh install.sh /path/to/workspace            # prints the block it would merge
sh install.sh /path/to/workspace --write    # merges into .bob/settings.json
export COUNTERSIGN_WORKSPACE=/path/to/workspace
```

Configuration is environment only, with no defaults: `COUNTERSIGN_WORKSPACE` is required,
`COUNTERSIGN_REQUIRE_PRIOR_READ=1` additionally refuses writes to paths this task never
observed. Ports: `COUNTERSIGN_PORT` (4319), `PORT` for the console (4311).

## Verification

```sh
python3 tests/test_gate.py         # 15 behaviour cases
python3 tests/test_matrix.py -j 6  # 500 case matrix across families of payloads and states
python3 tests/test_receipts.py     # 16 cases: receipts, chain, redaction, policy, replay
python3 scripts/acceptance.py      # the 21 step fresh machine run, against a live runtime
python3 countersign.py replay      # recompute every stored verdict from its own inputs
```

Each test builds a real git workspace, writes real files, and runs the gate as a subprocess,
asserting the exit code and the refusal code. The acceptance run creates a repository,
connects it, protects it, opens a session, records a read, changes the file from a second
process, attempts the edit, reads the refusal, refreshes the evidence, retries, verifies
the receipt chain and finally runs the self-test, printing what it observed at every step.

Interception is not simulated: the runtime invokes the gate command with the payload the
agent sends and keeps the exit code the process returned.

## What is not proven

- Whether the runtime's own edit path already refuses a write to a file changed since it
  was read. Its tool documentation describes no such behaviour, and silence is not
  evidence, but nothing here depends on it.
- What an `apply_diff` payload carries beyond path and diff: the refusal keys off path,
  digests and recorded observations only.
- Subagent digests: a subagent's observations arrive through the parent's tool results, so
  per-subagent manifests are not separated.
- Enforcement reach: the hook is installed per workspace or per machine, so a repository
  guarded on one machine is not guarded on another while the agent runs there. What the
  machine cannot do is hide a verdict: `countersign replay` re-derives every stored receipt
  from its own recorded inputs on any machine that has the receipts and the repository, and
  `.github/workflows/replay.yml` runs that on every push, then forges a verdict and asserts
  the replay fails. What is not built is organisation-wide enforcement as the default; the
  replay checks verdicts, it does not stop an edit on a machine that has no hook.
- Nothing here reads a vendor private API: the gate consumes the public hook payload plus
  the workspace itself.

## Layout

```
countersign.py              the gate
runtime/countersign_runtime.py   the local control plane (stdlib only, HTTP + SSE)
run.sh                      start runtime and console together
install.sh                  installs the gate and merges the hook block
landing/                    the Next.js console and product site
tests/test_gate.py          15 behaviour cases
tests/test_matrix.py        500 case matrix
tests/test_receipts.py      16 receipt, chain, redaction, policy and replay cases
scripts/acceptance.py       the 21 step fresh machine acceptance run
scripts/forge_a_verdict.py  forge a verdict, used by CI to prove the replay has teeth
.github/workflows/replay.yml  replay the committed bundle, then assert a forgery fails
scripts/acceptance_gate.sh  the same mechanism at gate level, no runtime
docs/LIVE_RUN.md            a refusal recorded from a real agent session
docs/MULTI_DEV_RUN.md       admitted before fetch, refused after
docs/SCENE_REVISION_MOVED.md  identical bytes, moved revision, refused
docs/evidence-store/        recorded stores from four real scenes
```
