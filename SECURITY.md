# Security notes

- The gate never executes a tool. It reads the payload, reads the workspace, and
  answers. Refusal is an exit code.
- Evidence is stored inside the governed workspace. Nothing is sent anywhere.
- No credentials are read or stored. The gate has no network access and no API keys.
- Paths are resolved against the workspace and anything outside it is refused
  (`OUTSIDE_WORKSPACE`), including traversal forms.
- Payloads that cannot be parsed, or that are not objects, fail closed.
- Hook commands in the shipped configuration contain the workspace path and no
  secrets; keep them out of world-readable paths if the workspace path itself is
  sensitive.
- The evidence log is append-only by convention, not by permission. For a
  tamper-evident trail, keep the workspace under version control and commit the
  events file, or export per-task records and store them outside the workspace.
