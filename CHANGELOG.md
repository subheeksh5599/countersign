# Changelog

## 1.0.0
- Gate with three modes: `session-start`, `record`, `check`, plus `probe` and `export`.
- Per-task manifests; resumed tasks keep their evidence.
- Refusal codes: `EVIDENCE_SUPERSEDED`, `CROSS_TASK_EVIDENCE`, `REVISION_MOVED`,
  `COMMAND_RESULT_CHANGED`, `UNSUPPORTED_SUBTASK_EVIDENCE`, `UNVERIFIED_TARGET`,
  `OUTSIDE_WORKSPACE`, `NO_MANIFEST`.
- Payload support for the real hook schema (`hook_event_name`, `tool_name`,
  `tool_input`) and the older synthetic one.
- Machine-wide and per-workspace installation, idempotent hook merging.
- Lens page rendered from real events; hashed per-task exports.
- Suites: 15 behaviour cases and a 500-case matrix.
