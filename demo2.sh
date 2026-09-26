#!/bin/sh
# The command scene: a result that changed underneath the task blocks the write,
# and blocks further state-changing commands. Real records, real exit codes.
# Usage: sh demo2.sh /path/to/workspace
set -u
WS="${1:?usage: sh demo2.sh /path/to/workspace}"
export COUNTERSIGN_WORKSPACE="$WS"
GATE="python3 .countersign/countersign.py"
cd "$WS" || exit 1

say() { printf '\n== %s ==\n' "$1"; }

say "task C opens and runs its test command"
printf '{"event":"SessionStart","session_id":"task_C"}' | $GATE session-start
printf '{"event":"PostToolUse","session_id":"task_C","tool":"execute_command","input":{"command":"npm test","output":"84 passing"}}' | $GATE record

say "the same command is run again and now reports a different result"
printf '{"event":"PostToolUse","session_id":"task_C","tool":"execute_command","input":{"command":"npm test","output":"83 passing"}}' | $GATE record
printf 'exit=%s\n' "$?"

say "task C proposes an edit while holding a contradicted result"
printf '{"event":"PreToolUse","session_id":"task_C","tool":"write_file","input":{"path":"src/sarif.ts","content":"// x"}}' | $GATE check
printf 'exit=%s\n' "$?"

say "task C proposes a destructive command"
printf '{"event":"PreToolUse","session_id":"task_C","tool":"execute_command","input":{"command":"rm -rf build"}}' | $GATE check
printf 'exit=%s\n' "$?"

say "what the task holds"
cat .countersign/tasks/task_C.json
