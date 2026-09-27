# Countersign — 5 minute video plan

Recorded entirely in the browser against the local console (`http://127.0.0.1:4311/console`)
with the runtime running. No terminal, no repository page, no slides. Every number on
screen is produced by the run that is happening.

Judged on problem, solution, value proposition, market analysis, revenue model, roadmap
and competitive analysis. Each row below maps to one of those.

| time | what is on screen | judged element |
|---|---|---|
| 0:00-0:20 | Open on the protect page, status bar already reading PROTECTED with a real repository, branch, HEAD, session, last verdict and latency. One sentence, spoken: the agent's own documentation says its memory is lossy and wrong facts stay in the transcript, and the documented fix is that a human notices. | problem (hook) |
| 0:20-0:45 | The documented quotes read out over the same page: compaction is lossy; wrong text keeps being treated as fact; the reliable fix is a new task; rollback excludes external changes. | problem |
| 0:45-1:30 | Explain the mechanism over the protect page: the session's held evidence table on the left (path, held sha256, current sha256, status), the intercepted call card, the security state listing hook installed, runtime connected, repository protected, receipt chain valid. Say the invariant out loud. | solution |
| 1:30-3:00 | Live refusal, driven from the self-test page: press "run countersign self-test". Watch the steps table fill in with real exit codes and wall times: session start, read through the gate, the second process changing the file, the edit refused at exit 2, the file untouched, the operator refresh, the retry admitted at exit 0, the edit applied. Land on run 1 REFUSED and run 2 ALLOWED with the held digest, the digest on disk and both receipts. | solution, application |
| 3:00-3:30 | Click through to the interceptor page: the refused call with its classification, reason `EVIDENCE_SUPERSEDED`, exit code 2, measured latency, the redacted arguments, and press replay check to show the same deterministic decision re-run now. Then the receipts page: the chain, then verify receipt, recomputing the hash on screen. | solution, application, proof |
| 3:30-4:00 | Value: an edit built on facts reality already invalidated never lands; parallel agents stop being invisible to each other; every task leaves a reviewable, verifiable receipt chain. Point at the evidence page filters (ALL, CURRENT, STALE, DELETED) and the per-item re-check and refresh. | value proposition |
| 4:00-4:30 | Market: platform and developer productivity teams running agents on shared repositories, and the risk owners who authorise that autonomy. The budget is change governance and controls. Measured value: stale-evidence edits refused, incidents avoided, rework not done. Say the honest caveat: enforcement is per machine, receipts are the artefact a CI job would replay. | market analysis |
| 4:30-4:45 | Revenue: per repository, an enterprise policy package, organisation-wide enforcement, exported evidence records for review. | revenue model |
| 4:45-4:55 | Roadmap: server-side receipt replay in CI, subtask evidence separated, machine-wide enforcement as the default, the same gate on every state-changing surface. | roadmap |
| 4:55-5:00 | Competitive: the field audits judgement, this audits identity. Close on the invariant. | competitive analysis |

## How to set up the recording

```sh
sh run.sh            # runtime on 4319, console on 4311
```

Then open `http://127.0.0.1:4311/console`, press "create demo repository", and the protect
page fills with that repository. The self-test page always builds a fresh repository of its
own, so it is safe to press as many times as a take needs.

## Rules for recording

- Show the product, not a terminal and not a repository page.
- Every number on screen comes from the run in progress. If a scene cannot be reproduced
  live, cut the scene rather than illustrate it.
- Never describe the console as a demo mode. It drives the same gate command the agent's
  hook runs, with the same payload, and shows the exit code that process returned.
- Say the not-proven list once, briefly. It is the reason to believe the rest.
- The recovery scene matters as much as the refusal. A gate that only blocks looks broken;
  a gate that blocks and shows the way back looks finished.
