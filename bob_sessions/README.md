# bob_sessions/

Evidence of genuine IBM Bob usage for this project, in the two forms the event asks for.

## Required artifact — the Bob IDE task header summary

Per the official hackathon guide, the qualifying artifact is the **task session summary
screenshot exported from the IDE**: open the task, then **Tasks → task header → summary →
PNG export**. `ide/` holds those exports.

That folder is deliberately empty. A rendered image of a terminal is not an IDE export, and
putting one there would claim something this repository cannot show. To fill it:

1. Open Bob in the IDE against this project's workspace.
2. Open the task from shared task history, using the task IDs in the table below.
3. Export its header summary PNG into `ide/`.

One export per person who actually drove a Bob task. If you are the only one who did, one
export is the complete set.

**Scrub credentials before committing.** The guide warns that IBM Bob or Cloud credentials
detected in a repository trigger account deactivation. Nothing in this repository holds key
material; the key is read from the environment at run time and is never printed.

## Supplementary evidence — Bob Shell (headless)

The guide marks `bob run` optional. Each `shell-*/` folder holds one real run:

- `prompt.md` — the exact prompt that was sent
- `transcript.txt` — the run's captured stdout, verbatim, with ANSI escapes stripped
- `task-summary.txt` — the Task Summary block Bob printed at the end of that run

| session | what it shows | task ID | cost | duration | tool calls |
|---------|---------------|---------|------|----------|------------|
| `shell-01-four-refusals` | one edit attempted four times across two write tools, refused every time | `eea2941f4db4a1f67c401695b74446d0` | 1.05 | 44.6s | 8 |

Nothing here is reconstructed. `transcript.txt` is the output of the command written in
`prompt.md`, cut to its last 70 lines exactly as it was captured, and its Task Summary block
is the one Bob printed. The same numbers appear in the README and the slide deck, taken from
this block rather than asserted separately.

The run is worth reading in full. Bob tries `apply_diff` three times, then reasons that
`search_and_replace` "performs an in-place substitution without the same evidence-digest
check" and tries that instead. The gate refuses that one too, and Bob's closing report names
the actual cause: a concurrent writer inside the read-to-write window.

## Where the code Bob was driven against lives

- `.bob/settings.json` hook block — see `docs/HOOKS.md` and `install.sh`
- The gate itself — `countersign.py`, driven by `runtime/countersign_runtime.py`
- The captured payloads from a real Bob workspace — `tests/fixtures/real_payloads.json`
- The refusal receipts this session produced — `docs/evidence-store/live_2026_09_27/`
