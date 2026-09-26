# Architecture

One process, three modes, one store.

```
SessionStart   -> session-start  -> .countersign/tasks/<task>.json   (manifest)
PostToolUse    -> record         -> manifest gains observations and command results
PreToolUse     -> check          -> reads the manifest, recomputes digests,
                                    writes a receipt, exits 0 or 2
```

Store layout inside the governed workspace:

```
.countersign/
  tasks/<task>.json     one manifest per task: commit, observations, commands,
                        contradictions, provenance per observation
  events.jsonl          append-only log of observations and verdicts
  payloads/             raw hook payloads, written only in probe mode
  exports/<task>.json   hashed evidence record per task
```

Design rules the code holds to:

1. No model participates in a verdict. Digests, task identity and revision identity
   decide, so the same inputs always produce the same answer.
2. Fail closed. No manifest, unreadable payload, payload that is not an object, or
   an unresolvable workspace all refuse rather than permit.
3. One manifest per task. A resumed task keeps the evidence it already holds; a
   second task cannot overwrite another task's evidence.
4. Evidence is keyed by workspace-relative path, and anything outside the workspace
   is refused rather than silently rewritten into a relative path.
5. Every verdict writes a receipt: a digest over the decision and its inputs.
