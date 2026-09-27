# The runtime

One process, stdlib only, on `http://127.0.0.1:4319`. It holds no evidence of its own.
Everything it serves is read from the store the gate wrote in the workspace under control
(`.countersign/tasks/*.json`, `events.jsonl`, `receipts/*.json`) or measured with a real
`git` or filesystem call.

```
python3 runtime/countersign_runtime.py          # or: sh run.sh --runtime-only
COUNTERSIGN_PORT=4399 python3 runtime/countersign_runtime.py
```

State that survives restarts lives in `~/.countersign/runtime.json`: the connected
repository, whether it was created as a demo, and nothing else. If
`COUNTERSIGN_WORKSPACE` is set, it wins over the stored repository and the runtime binds
to that workspace instead.

## Two loops

**The watcher** runs every half second and does three things, all of them real:

1. reads new lines from the gate's event log and publishes them on the stream, so
   `session_started`, `file_read`, `tool_refused` and the rest reach the console as the
   gate writes them;
2. re-hashes every file the active session holds. When a held digest no longer matches
   the file on disk it publishes `filesystem_changed` with the held and current digests
   and the status `STALE`, once per change. A file that disappears publishes `DELETED`;
3. compares `git rev-parse HEAD` with the last value it reported and publishes
   `git_head_changed` when the commit moves.

**The HTTP layer** serves the pages and performs the operations the console asks for.
Reads never mutate anything. The writes, and what they actually do:

| Route | Real effect |
|---|---|
| `POST /api/repo/connect` | stores the workspace path; every later read uses it |
| `POST /api/repo/demo` | creates a real git repository under `~/.countersign/demo-repo` and connects it |
| `POST /api/repo/protect` | runs `install.sh <workspace>`, which copies the gate in and merges the hook block into the workspace settings |
| `POST /api/repo/stop` | edits the settings file and removes the hook entries that carry the gate command |
| `POST /api/repo/refresh` | re-reads git state and publishes whether HEAD moved |
| `POST /api/session/start` | runs the gate's `session-start` mode with a real payload |
| `POST /api/evidence/read` | runs the gate's `record` mode for one path, so the digest is recorded as evidence |
| `POST /api/evidence/refresh` | runs the gate's `refresh` mode: re-hashes the held files and rewrites the manifest |
| `POST /api/evidence/recheck` | runs the gate's `recheck` mode: a verdict, no receipt, no event |
| `POST /api/interceptor/attempt` | runs the gate's `check` mode with the payload the agent sends and keeps the exit code |
| `POST /api/interceptor/replay` | re-runs the deterministic check for a stored receipt against the repository as it is now |
| `POST /api/receipts/<id>/verify` | strips `receipt_hash` from the stored file, hashes the rest, compares |
| `POST /api/selftest` | builds a fresh repository from nothing and runs the full sequence in it |
| `POST /api/demo/start` | the same sequence against the demo repository |

## The sequence behind self-test and demo

Real repository, real files, real subprocess calls to the gate, real exit codes:

1. create the repository and commit a source file and a config file;
2. `session-start`: a session opens an evidence manifest;
3. `record` a read of `src/config.ts`, so its SHA-256 becomes held evidence;
4. a second process rewrites that file (a real `sh -c` write, not a variable swap);
5. `check` an `apply_diff` on the path: the gate refuses, exit code 2, receipt written;
6. confirm the file on disk still holds the value the other process wrote;
7. `refresh`: the runtime re-hashes the held files and rewrites the manifest;
8. `check` the same call again: admitted, exit code 0, second receipt written;
9. the edit is applied for real, and the new digest is recorded.

Both receipts are returned with the run, chained to each other, and the file content after
the run is shown as it is on disk.

## Events

`runtime_hello`, `session_started`, `file_read`, `evidence_created`, `filesystem_changed`,
`git_head_changed`, `tool_intercepted`, `evidence_checked`, `tool_refused`, `tool_allowed`,
`receipt_created`, `evidence_refreshed`, `repository_connected`, `protection_started`,
`protection_stopped`, `git_state_refreshed`, `selftest_started`, `selftest_step`,
`selftest_finished`, `demo_started`, `check_replayed`, `watcher_error`.

Gate events are forwarded inside a `gate_event` envelope so a client can see the raw line
the gate appended. `GET /api/stream` is server sent events, one JSON object per `data:`
line, with a keepalive comment every fifteen seconds. The console subscribes once per
page and refetches when anything arrives, so no browser side timer polls the runtime.

## Reading the console

`GET /api/status` answers the five questions the homepage is built around: whether the
repository is protected, what the session holds, whether any held evidence is stale, what
the last intercepted call did, and what is on the last receipt. `hook_scope` distinguishes
a workspace install from a machine wide one, because they are different claims: a workspace
settings file protects that repository, while the shared settings file protects every
repository the agent opens on the machine.

`GET /api/evidence` computes each row from the manifest and the filesystem at request time,
so `status` is always one of `CURRENT`, `STALE` or `DELETED` and never a cached verdict.
`GET /api/interceptor` pairs each `tool_intercepted` event with the receipt that carries its
verdict, in order, because two calls can land in the same second and a timestamp comparison
alone would hand both of them the first receipt.

## What the runtime does not do

- It does not police the agent's own filesystem access. It runs the same gate command the
  hook runs, with the same payload, and reports what that process returned.
- It does not referee a change that exists only on another machine. Two clones have two
  manifests; an unfetched remote change is invisible to any local check.
- It does not judge. There is no model in the verdict path and no model call anywhere in
  the runtime.
