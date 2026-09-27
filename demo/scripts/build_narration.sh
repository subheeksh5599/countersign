#!/bin/sh
# Narration for the Countersign demo. One line per file, male voice, edge TTS.
#
#   sh demo/scripts/build_narration.sh
#
# Voice: en-US-AndrewMultilingualNeural. The delivered speech is measured (median F0) in
# verify_cut.sh; a value in the 100-130 Hz band is the adult male range.
#
# The demo section runs longer than the first cut. The submission rules ask for at least 90
# seconds of the solution on screen, and the first cut carried 44s of it. The added lines
# cover the self-test run and the published record page, both real product surfaces.
set -e
OUT="${1:-/tmp/csign_tts}"
VOICE="en-US-AndrewMultilingualNeural"
RATE="+2%"
TTS=$(command -v edge-tts || ls /home/arch/.hermes/installs/*/environments/*/venv/bin/edge-tts 2>/dev/null | head -1)
[ -n "$TTS" ] || { echo "edge-tts not found" >&2; exit 1; }

mkdir -p "$OUT"

say() {  # say <file> <text>
  "$TTS" --voice "$VOICE" --rate="$RATE" --text "$2" --write-media "$OUT/$1.mp3" >/dev/null 2>&1
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$1.mp3")
  printf '%-4s %6.2fs  %s\n' "$1" "$d" "$2"
}

# --- intro -------------------------------------------------------------------
say i1 "An agent reads a file, and then acts on what it read."
say i2 "By the time it acts, that file may already say something else."
say i3 "Countersign compares the evidence a task is holding with the repository as it is now."
say i4 "Different, and the edit does not run."
say i5 "Countersign. The local control plane for an AI coding agent."

# --- the recording -----------------------------------------------------------
say d1 "Countersign sits in front of every state-changing tool call an agent makes."
say d2 "It holds one rule. No write may use repository evidence whose identity is no longer current."
say d3 "The verdict is a hash comparison, and no model touches it."
say d4 "Here the console runs one real agent turn, against a real repository."
say d5 "The agent reads the file, and that read is recorded as evidence."
say d6 "A second process moves the file while the agent is still working."
say d7 "The write comes back refused, exit code two, with the digest the task held beside the digest on disk."
say d8 "The console can also run its acceptance check on demand, and show every step passing."
say d9 "Nothing on these pages is a stored claim. Every line comes from the run in front of you."
say d10 "Evidence: each session's manifest, with its refusals and admissions counted."
say d11 "Interceptor: every call the hook saw, classified, with its verdict."
say d12 "Receipts: the store replays, both verdicts re-derive, and none fails."
say d13 "The published record is checkable too. The site recomputes these receipts in your browser, and prints the chain head it computes beside the one the command line prints."
say d14 "Countersign. Local first, and no model in the verdict."
