# The refusal on the real hook path

The gate is exercised against the payloads a live session actually emitted, not against
shapes written to fit it. `tests/fixtures/real_payloads.json` holds them verbatim, captured
by `probe` mode; `scripts/replay_real_refusal.sh` feeds them to the same modes the installed
hook invokes.

Reproduce it:

```
sh scripts/replay_real_refusal.sh
```

What happens, in order:

| Step | Payload | Mode | Exit | Result |
|---|---|---|---|---|
| 1 | `SessionStart` | `session-start` | 0 | the runtime opens a task |
| 2 | `read_file` PreToolUse | `check` | 0 | a read is classified, not gated |
| 3 | `read_file` PostToolUse | `record` | 0 | the read becomes the evidence this task holds |
| 4 | *(a second process rewrites the file)* | — | — | the file moves inside the window |
| 5 | `apply_diff` PreToolUse | `check` | **2** | the state-changing call is refused |

The refusal at step 5, from a real `apply_diff` payload whose target is
`/tmp/bob_probe_ws/pricing.ts`:

```
REFUSED: EVIDENCE_SUPERSEDED
About to modify pricing.ts.
Evidence this task holds: baa5252515ea.
Digest on disk now: f24af5254d22.
  EVIDENCE_SUPERSEDED: baa5252515ea -> f24af5254d22 (the file changed after this task observed it)
  REVISION_MOVED: a512df3add44 -> 2522bc69c806 (this path was committed at a different revision after the task observed it)
Required recovery:
  1. open a fresh task
  2. re-observe pricing.ts
  3. rerun the affected commands
  4. record the new evidence manifest
Refusal receipt: 582b05e62d75bb15b36dcc508822961aea3895dac43a3dfffbd203af87d4454e
Receipt id: rcpt_00001_3332aac2029a | latency 109 ms
The action did not happen.
```

The two digests are stable across runs because the file content either side of the window is
fixed. The receipt hash and id change every run, because the receipt records the time it was
written — quote them from your own run rather than from this page.

## What this does and does not cover

It covers the decision: the real payload fields (`hook_event_name`, `tool_name`, `tool_input`,
`session_id`) reach the gate through the same entry point the hook uses, and the refusal is
reached from a real file change rather than a staged one.

It does not cover the wiring inside the vendor CLI: the process that invokes the gate on each
tool call is the runtime's own hook mechanism, installed by `install.sh`. This script proves
the gate's half of that contract with real inputs. `docs/LIVE_RUN.md` covers the other half —
a real session where four state-changing attempts were each refused, with the receipts to
match.

The payload carries the pending diff in `tool_input.diff` and the gate deliberately does not
read it, which is why a wrong edit to an unchanged file is admitted. `docs/LIMITS.md` states
that boundary.
