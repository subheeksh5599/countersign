# Subtasks and attributed calls

A conclusion that arrives without the observation behind it is refused.

When a call is attributed to a subtask (`tool_input.subtask`), the gate requires an
observation of that same path credited to that same subtask before the write is
allowed. Otherwise:

```
REFUSED: UNSUPPORTED_SUBTASK_EVIDENCE
The proposed change to src/auth.ts is attributed to subtask sub_1.
No observation of that path by that subtask is on record.
The conclusion arrived without evidence behind it.
Required recovery: let the subtask observe the path, or re-observe it in this task.
```

Provenance is recorded per observation (`direct` or `subagent:<id>`) and shown in
the lens page under "who observed what", so a reviewer can see which conclusions
came from delegated work.
