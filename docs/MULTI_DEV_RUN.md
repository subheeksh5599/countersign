# Multi-developer run, verbatim

Command: `sh scripts/demo_multi_developer.sh`

```
warning: You appear to have cloned an empty repository.

== developer A: task opens and reads pricing.ts ==
{"verdict": "ADMITTED", "note": "evidence recorded"}
exit=0

== developer B: edits and commits the same path, pushes ==

== developer A's task tries to edit, before the clone knows anything ==
{"verdict": "ADMITTED", "note": "evidence current, receipt 92def37c818c"}
exit=0

== the clone fetches the change ==
export const rate = 9

== the same task tries the same edit again ==
Refusal receipt: ba80bac2a3db654fb0686c35e2a14d30cdf9d07fee23c232ef78ec3039c58490
The action did not happen.
exit=2

== what the record shows ==
{"exported": ["task_dev_a_pricing.json"], "dir": "/tmp/cs_multi/devA/.countersign/exports"}
record: task_dev_a_pricing.json
  task: task_dev_a_pricing | opened on commit: 5be91599eef3be4b110a6e864c4a01e3e3c7f232
  verdicts: [('ADMITTED', None), ('REFUSED', ['EVIDENCE_SUPERSEDED', 'REVISION_MOVED'])]
  record hash: 974bf0fca73a59e474af3ee43caeefc2801d04a5c55dca9b26e25cf7d10f5495

Honest note: the first verdict was ADMITTED because the clone really had not
changed. A local gate cannot referee a change that lives on another machine; it
refuses the moment the clone has the change. That is what the exported receipt is
for: the server-side half.
```
