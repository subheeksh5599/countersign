# Roadmap

1. Ship the hook block as an organisation-wide default, so every workspace refuses
   stale-evidence edits without per-project setup.
2. Separate manifests per subtask once the payload identifies subtasks, and refuse
   parent writes that lean on a subtask's unrefreshed observation.
3. Command contradictions scoped to the state the command reads, instead of the whole
   task, to cut false positives from outputs that change for benign reasons.
4. Sign the evidence records. `countersign export` writes one hashed page per task today
   and the receipts are hash-chained, but nothing is signed, so authorship is not proven.
5. Extend the same fall-closed pattern to every state-changing surface the runtime
   exposes, including files outside the workspace when a task is explicitly granted
   them.
