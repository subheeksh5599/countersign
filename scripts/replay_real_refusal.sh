#!/bin/sh
# Drive the REAL captured hook payloads through the gate and produce a refusal.
#
# The payloads are the ones a live session emitted (glob, read_file, apply_diff) and
# they are stored verbatim in tests/fixtures/real_payloads.json. Nothing here is
# synthesised: the same three payloads a real task produced are fed to the same mode
# the installed hook invokes, and the check refuses with exit 2.
#
# Sequence, exactly the one that matters:
#   session-start  -> the runtime opens a task
#   check          -> a read is classified, not gated
#   record         -> the read becomes the evidence this task holds
#   (a second process rewrites the file inside the window)
#   check          -> the state-changing call is refused, and says which fact moved
#
# Usage: sh scripts/replay_real_refusal.sh [/path/to/workspace]
#
# Default workspace is the one the captured payloads name (they carry absolute paths,
# so replaying them anywhere else refuses for the wrong reason: OUTSIDE_WORKSPACE).
set -u

WS="${1:-/tmp/bob_probe_ws}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
GATE="$ROOT/countersign.py"
FIX="$ROOT/tests/fixtures/real_payloads.json"

rm -rf "$WS"; mkdir -p "$WS"; cd "$WS"
git init -q . 2>/dev/null
printf 'export const rate = 1\n' > pricing.ts
git add pricing.ts 2>/dev/null
git -c user.email=gate@countersign -c user.name=countersign commit -qm init 2>/dev/null

export COUNTERSIGN_WORKSPACE="$WS"

pay() { # $1 = mode, $2 = payload key, feeds the stored payload on stdin
  python3 -c "
import json, sys
sys.stdout.write(json.dumps(json.load(open('$FIX'))['$2']))
" | python3 "$GATE" "$1"
}

echo "workspace $WS"
echo
echo "\$ countersign session-start   <- SessionStart payload"
pay session-start 0000_SessionStart.json; echo "exit $?"
echo
echo "\$ countersign check           <- read_file PreToolUse (classified, not gated)"
pay check 0003_PreToolUse.json; echo "exit $?"
echo
echo "\$ countersign record          <- read_file PostToolUse (the read becomes evidence)"
pay record 0004_PostToolUse.json; echo "exit $?"
echo
echo "-- a second process rewrites the file inside the read -> write window --"
printf 'export const rate = 1\nexport const label = "formatting pass"\n' > pricing.ts
git add pricing.ts 2>/dev/null
git -c user.email=gate@countersign -c user.name=countersign commit -qm "unrelated change" 2>/dev/null
echo
echo "\$ countersign check           <- apply_diff PreToolUse (the state-changing call)"
pay check 0005_PreToolUse.json; rc=$?
echo "exit $rc"
echo
if [ "$rc" -eq 2 ]; then
  echo "the action did not happen. this is the refusal the hook produces in a live session."
else
  echo "UNEXPECTED: the check admitted a call whose evidence moved (exit $rc)"
  exit 1
fi
