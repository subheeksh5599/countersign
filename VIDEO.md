# Countersign — 5 minute video plan

Judged on problem, solution, value proposition, market analysis, revenue model,
roadmap and competitive analysis. Every second below maps to one of those. The
refusal must be visible on screen — it is the only scene that cannot be faked.

| time | what is on screen | judged element |
|---|---|---|
| 0:00-0:20 | One sentence, spoken over the lens page: the agent's own documentation says its memory is lossy and wrong facts stay in the transcript. | problem (hook) |
| 0:20-0:50 | The documented quotes, one per card: compaction is lossy; wrong text keeps being treated as fact; the reliable fix is a new task; rollback excludes external changes. | problem |
| 0:50-1:40 | How it works, over the lens: session opens a manifest, every read and command result gets a digest and a receipt, the tool boundary refuses when the digest no longer matches. Name the refusal codes out loud. | solution |
| 1:40-2:40 | Live: task A observes a file. Task B, a second task on the same repository, changes it — the file on screen really changes. Task A proposes its edit. The write is refused, exit code 2, both digests shown, recovery steps listed. | solution, application |
| 2:40-3:10 | Live: task A opens fresh, re-observes, the same edit is admitted with a receipt. Then the command scene: a recorded test result changes and the write and the destructive command are both refused. | solution, application |
| 3:10-3:30 | Value: an edit built on facts reality already invalidated never lands; parallel agents stop being invisible to each other; each task leaves a reviewable evidence record. | value proposition |
| 3:30-4:10 | Market: platform and developer-productivity teams running agents on shared repositories, and the risk owners who authorise that autonomy. The budget is change governance and controls. Measured value: stale-evidence edits refused, incidents avoided, rework not done. | market analysis |
| 4:10-4:30 | Revenue: per repository, an enterprise policy package, organisation-wide enforcement through the runtime's enforced-hook mechanism, and exportable evidence records for review. | revenue model |
| 4:30-4:50 | Roadmap: hooks in one workspace; subtask evidence separated; organisation-wide default; exported evidence records; the same gate extended to every state-changing surface. | roadmap |
| 4:50-5:00 | Competitive: the field audits judgement, this audits identity. Close on the invariant. | competitive analysis |

## Rules for recording
- Show the product, not a terminal and not a repository page. The refusal, the lens
  and the recovery are the product surface.
- Every number on screen comes from a real run. If a scene cannot be reproduced in
  the installed runtime, cut the scene rather than illustrate it.
- Say the not-proven list out loud once, briefly: it is the reason to believe the
  rest.
- The recovery scene matters as much as the refusal. A gate that only blocks looks
  broken; a gate that blocks and shows the way back looks finished.
