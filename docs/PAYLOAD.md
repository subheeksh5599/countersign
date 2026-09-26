# Hook payloads

Observed in a live session, captured by `probe` mode and stored verbatim in
`tests/fixtures/real_payloads.json`.

SessionStart:

```json
{ "cwd": "/workspace", "hook_event_name": "SessionStart",
  "session_id": "<task id>", "source": "startup" }
```

PreToolUse:

```json
{ "cwd": "/workspace", "hook_event_name": "PreToolUse", "session_id": "<task id>",
  "tool_name": "read_file", "tool_use_id": "tooluse_...",
  "tool_input": { "path": "/workspace/pricing.ts" } }
```

PostToolUse adds the result of the call:

```json
{ "cwd": "/workspace", "hook_event_name": "PostToolUse", "session_id": "<task id>",
  "tool_name": "read_file", "tool_use_id": "tooluse_...",
  "tool_input": { "path": "/workspace/pricing.ts" },
  "tool_response": "Contents of file pricing.ts:\n\n1 | export const rate = 1\n2 | " }
```

Facts that shaped the implementation:

- The field names are `hook_event_name`, `tool_name`, `tool_input`; the session id is
  the same id the runtime prints as the task id, so a receipt can be joined to the
  runtime's own task record.
- Paths arrive absolute and inside `cwd`, which is why the gate keys evidence by
  workspace-relative path and refuses anything outside.
- The edit tools observed are `apply_diff` and `search_and_replace`; both carry the
  pending change, so a payload never has to be guessed at.
- The gate accepts the older synthetic field names (`event`, `tool`, `input`) as
  well, so recorded fixtures and live payloads run through one code path.
