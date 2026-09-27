#!/bin/sh
# Narration for the Countersign demo. One line per file, male voice, edge TTS.
#
#   sh demo/scripts/build_narration.sh
#
# Voice: en-US-AndrewMultilingualNeural. The delivered speech is measured (median F0) in
# verify_cut.sh; a value in the 100-130 Hz band is the adult male range.
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
say d1 "Countersign refuses an edit when the facts behind it are no longer true."
say d2 "The console drives a real turn against a demo repository, with a second process moving the file."
say d3 "The agent reads, records that digest as evidence, then asks to change the file."
say d4 "Exit two. The evidence the task held is older than the file on disk, so the edit never runs."
say d5 "Each session keeps its own manifest: files, refusals, receipts."
say d6 "Every call is kept, classified, with its verdict."
say d7 "Replays re-derive both verdicts. None fails."
