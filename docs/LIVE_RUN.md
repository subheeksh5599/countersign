# A live refusal

Recorded from a real session, one task, real cost, real exit code. The harness
writes the path inside the read -> write window to stand in for a concurrent task.

The agent read the file, and the file changed before the edit landed:

```
Tool: apply_diff
Args:
- path: /workspace/pricing.ts
- diff: <<<<<<< SEARCH
:start_line:1
-------
export const rate = 1
=======
export const rate = 5
>>>>>>> REPLACE
```

The gate refused the call, exit code 2:

```
REFUSED: EVIDENCE_SUPERSEDED
About to modify pricing.ts.
Evidence this task holds: 75309f9e6112.
Digest on disk now: c56e4af78a4a.
  EVIDENCE_SUPERSEDED: 75309f9e6112 -> c56e4af78a4a (the file changed after this task observed it)
Required recovery:
  1. open a fresh task
  2. re-observe pricing.ts
  3. rerun the affected commands
  4. record the new evidence manifest
Refusal receipt: a0116af8b77c77062d88bccc068a3faf8de49531e6bf27c18eabacfbb9db1f1c
The action did not happen.
```

The agent's own report of what happened:

> The file on disk changed between my read and the attempted write — the digest no
> longer matches. The safety guard correctly blocked the edit. The file's current
> content differs from what I observed (export const rate = 1). To proceed safely I
> need to re-read the current state before modifying it.

The file on disk was not modified. The verdict and its receipt are in
`.countersign/events.jsonl`.

## Second live run: 2026-09-27, headless task, real receipts

A headless task on a real workspace with the workspace hook block installed. Task id
`eea2941f4db4a1f67c401695b74446d0`, cost 1.05 Bobcoins, 44.6 seconds, 8 tool calls.

The agent read `pricing.ts` and then attempted the edit four times with three different
tools. Every attempt was refused at exit code 2 with `EVIDENCE_SUPERSEDED`, and each one
wrote a receipt file:

```
rcpt_00000_d5b43485bfce  apply_diff          REFUSED  exit 2  chained to nothing
rcpt_00001_c2f764034810  apply_diff          REFUSED  exit 2  chained to rcpt_00000
rcpt_00002_e8659a4144cc  apply_diff          REFUSED  exit 2  chained to rcpt_00001
rcpt_00003_77b2ab6baab7  search_and_replace  REFUSED  exit 2  chained to rcpt_00002
```

`pricing.ts` after the run still holds the text the concurrent writer put there: the
refused calls changed nothing. The agent's own closing message:

> Once that process is stopped, re-run the task and the change rate = 1 -> rate = 5 will
> apply cleanly. The target line is on line 1 of the file and the content is
> straightforward; it will succeed as soon as the file is stable.

That is the product's claim written by the agent itself: the edit did not land while the
evidence was stale, and the way forward is to make the file stable and act on current
evidence.

The run also exposed a real installation defect. The machine-wide block was still
pointing at an older build, so both gates observed each call: 4 intercepted calls produced
8 verdict events and 4 receipt files, because the older copy appended a verdict without
writing a receipt. With one gate installed the counts are equal, verified on a separate
workspace: 3 intercepted calls, 3 verdict events, 3 receipt files, all hashes recomputed
and all links in the chain intact. `install.sh` now warns when both blocks are present.
