# Narration — Countersign demo

Delivered: `demo/media/countersign-demo.mp4` — **72.8s**, 1364x766, 30fps, male voice.
Standalone intro for a social post: `demo/media/countersign-intro.mp4` — **26.5s**.
Source recording: `/home/arch/Videos/recording_2026-09-27_14.35.18.mp4` (122.6s, silent, VFR).
Intro composition: `demo/intro/` (hyperframes, 1920x1080, rendered then scaled to the recording).

Twelve lines, 56.3s of speech across 72.8s. The refusal itself is deliberately silent: the
line before it ends at 45.9s and the next begins at 48.0s, so the verdict and both digests
land without a voice over them.

## Voice

edge TTS, `en-US-AndrewMultilingualNeural`, `--rate=+2%`. Measured median F0 of the delivered
audio is **115.9 Hz**, inside the adult male band (100-130 Hz), so the claim "male voice" is
measured rather than asserted. The machine's configured TTS default is a female voice and that
config is agent-protected, so narration was generated with the bundled `edge-tts` binary and
`~/.hermes/config.yaml` was not touched.

Same line, three voices, to pick from — `demo/media/voice-samples/`:
`en-US-AndrewMultilingualNeural` (delivered, 3.41s), `en-US-BrianMultilingualNeural` (3.46s),
`en-GB-RyanNeural` (3.79s). Switching is one line in `demo/scripts/build_narration.sh`.

## What was kept, and what was cut

| kept | source range | length | what it shows |
|------|--------------|--------|----------------|
| 1 | 3.5 – 8.0 | 4.5s | the claim on the site, then the failure story |
| 2 | 41.5 – 57.0 | 15.5s | the operator bar, create demo repository, run one real agent turn |
| 3 | 57.0 – 67.5 | 10.5s | the refusal: step table, REFUSED / EVIDENCE_SUPERSEDED, live events, held vs disk |
| 4 | 91.5 – 96.0 | 4.5s | evidence: each session's manifest with refusals and admissions counted |
| 5 | 96.0 – 100.0 | 4.0s | interceptor: every intercepted call, classified, with its verdict |
| 6 | 102.0 – 106.4 | 4.4s | receipts: replay both receipts, 0 failed, held for 3.1s at the end |

| removed | source range | why |
|---------|--------------|-----|
| the rest of the landing page | 0 – 3.5, 8.0 – 41.5 | scrolling with no action; the four seconds kept carry the claim |
| dead time in the console | inside 41.5 – 57.0 | frames where nothing changed while the page sat idle |
| the self-test page | 67.5 – 91.5 | the page's own prose with no result on screen; the evidence table two beats later is the same claim with numbers |
| the static record page | 107 – 122 | it is a published snapshot of a store, not the product, and the browser's transfer chrome is visible while it loads |

## Lines, and where each lands

| line | at | length | over |
|------|----|--------|------|
| i1 | 0.6s | 3.4s | intro: an agent reads, then acts |
| i2 | 5.5s | 3.7s | intro: the file moved after the read |
| i3 | 10.4s | 5.8s | intro: the comparison |
| i4 | 17.0s | 2.4s | intro: REFUSED |
| i5 | 20.8s | 4.4s | intro: the name |
| d1 | 27.0s | 4.1s | landing: the claim |
| d2 | 32.0s | 6.9s | console: a real turn, with a second process moving the file |
| d3 | 39.8s | 6.1s | console: read, recorded as evidence, then the ask |
| d4 | 48.0s | 6.1s | the refusal: exit 2, older evidence, the edit does not run |
| d5 | 57.3s | 5.4s | evidence: each session's manifest |
| d6 | 63.5s | 4.4s | interceptor: every call kept and classified |
| d7 | 68.8s | 3.7s | receipts: replays re-derive both verdicts, none fails |

## Text as spoken

**i1** — An agent reads a file, and then acts on what it read.
**i2** — By the time it acts, that file may already say something else.
**i3** — Countersign compares the evidence a task is holding with the repository as it is now.
**i4** — Different, and the edit does not run.
**i5** — Countersign. The local control plane for an AI coding agent.
**d1** — Countersign refuses an edit when the facts behind it are no longer true.
**d2** — The console drives a real turn against a demo repository, with a second process moving the file.
**d3** — The agent reads, records that digest as evidence, then asks to change the file.
**d4** — Exit two. The evidence the task held is older than the file on disk, so the edit never runs.
**d5** — Each session keeps its own manifest: files, refusals, receipts.
**d6** — Every intercepted call is kept, classified, with its verdict.
**d7** — Replays re-derive both verdicts. None fails.

## Reproduce and check

```sh
sh demo/scripts/build_narration.sh      # 12 lines of speech
sh demo/scripts/build_cut.sh            # cut + narration -> demo/media/countersign-demo.mp4
sh demo/scripts/build_intro_clip.sh     # the standalone intro -> demo/media/countersign-intro.mp4
sh demo/scripts/verify_cut.sh           # fails loudly, see below
```

`verify_cut.sh` checks the delivered file, not the intent: duration in range, an audio stream
present, every one of the 12 lines starting within 0.35s of where it was planned, a silence of
at least 0.9s covering 46.4-47.9s so nothing is spoken over the refusal, at least three frames
carrying REFUSED / EVIDENCE_SUPERSEDED, no frame carrying a cold loader, browser transfer
chrome, an error page or the static record page, and median F0 inside the male band.
