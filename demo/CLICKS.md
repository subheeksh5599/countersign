# Clicks — what the recording shows

Website only. No terminal, no editor, no repository browser. Start the stack once
(`sh run.sh`), then everything below happens in the browser at http://127.0.0.1:4311/console.

## The run captured

1. Open `/` — the landing page. Scroll to **Boundary**: "Three guarantees, all enforced before
   the call runs", then past **Two tasks, one file**. *(kept: 3.5-8.0s)*
2. Open `/console`. The status strip reads PROTECTED, the repository is
   `.countersign/demo-repo`, receipts 0, no verdict yet.
3. Press **create demo repository**. A real git repository is written under
   `~/.countersign/demo-repo` and the console switches to it. *(kept from 41.5s)*
4. Press **protect** — the hook is installed into that repository's settings file.
5. In **RUN AN AGENT TURN**, the request is `set RETRY_LIMIT to 5 in src/config.ts`, driver
   `auto`, and **second writer moves the file** is ticked. Press **run agent turn**.
6. The step table fills in: `plan`, `session_start` ADMITTED, `read_file` (digest recorded as
   evidence), `holding` — the file changed under the task — `apply_diff` **exit 2 REFUSED**,
   `stopped`. Driver `reference`, agent exit 2, 1 receipt written, ~2.2s. *(kept to 57.0s)*
7. Scroll down: **REFUSED: EVIDENCE_SUPERSEDED** on `src/config.ts`, live events
   (`tool_refused`, `evidence_checked`, `filesystem_changed`), and the held digest next to the
   digest on disk. *(kept: 57.0-67.5s, the refusal lands here)*
8. `/console/evidence` — every session in the store with files, observations, refusals,
   admissions and receipts. *(kept: 91.5-96.0s)*
9. `/console/interceptor` — every intercepted call with its class, target, verdict, reason,
   exit code, latency and receipt. *(kept: 96.0-100.0s)*
10. `/console/receipts` — press **replay receipts**: two receipts re-derived, 0 failed, each
    row PASS with hash, chain and follows columns, chain head shown. *(kept: 102.0-106.4s,
    held for 3.1s)*

## Not in the video

- The self-test page (67.5-91.5s) — its prose with no result on screen.
- GitHub Pages and the published snapshot page (107-122s) — a static record of a store, not the
  product, and the browser's transfer chrome shows while it loads.
- Any terminal. The gate, the runtime and the receipts are all reached through the console.
