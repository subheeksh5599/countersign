# Wiring the gate

The gate is driven by the runtime's lifecycle hooks. Three events are used.

| event | mode | why |
|---|---|---|
| SessionStart | `session-start` | opens the evidence manifest for the task |
| PostToolUse | `record` | digests every file read and every command result |
| PreToolUse | `check` | admits or refuses the proposed state-changing call |

The block, matching the documented schema (`hooks` -> event -> array of
`{matcher, hooks:[{type, command, timeout}]}`):

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
                     "command": "COUNTERSIGN_WORKSPACE=__WS__ python3 __WS__/.countersign/countersign.py session-start",
                     "timeout": 10 } ] }
    ],
    "PostToolUse": [
      { "matcher": "^(read_file|execute_command|run_command|shell|bash)$",
        "hooks": [ { "type": "command",
                     "command": "COUNTERSIGN_WORKSPACE=__WS__ python3 __WS__/.countersign/countersign.py record",
                     "timeout": 10 } ] }
    ],
    "PreToolUse": [
      { "matcher": ".*(apply_diff|write_file|search_and_replace|edit_file|delete|move|command|shell|bash).*",
        "hooks": [ { "type": "command",
                     "command": "COUNTERSIGN_WORKSPACE=__WS__ python3 __WS__/.countersign/countersign.py check",
                     "timeout": 10 } ] }
    ]
  }
}
```

`install.sh --write <workspace>` substitutes the workspace path and merges the
block into that workspace's settings file. `install.sh --global` installs the gate
machine-wide and merges a block that resolves the workspace from the `cwd` every
hook payload carries, so no per-project configuration is needed.

Notes that matter in practice:

- Workspace hooks are skipped when the folder is not trusted; run the runtime with
  its trust flag for the session that should be gated.
- Only PreToolUse and the prompt-submit event can block. A refusal is exit code 2.
- The default timeout is 10 seconds and can be overridden per hook. A check costs
  308 ms against a manifest holding 200 observations, measured over 20 runs on a
  two-core laptop — 30x inside the default timeout.
- A crash in a hook is not a refusal. The gate therefore fails closed on its own
  errors: unreadable payload, wrong payload type, or no resolvable workspace all
  exit 2.
- Installing both the global and the workspace block runs the gate twice per call.
  The installer is idempotent, but choosing one of the two is the cleaner setup.
