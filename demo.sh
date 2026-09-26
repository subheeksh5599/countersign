#!/bin/sh
# The two-task scene, reproducible. Usage: sh demo.sh /path/to/workspace
# Nothing here is simulated: a second task really rewrites the file on disk.
set -u
WS="${1:?usage: sh demo.sh /path/to/workspace}"
export COUNTERSIGN_WORKSPACE="$WS"
GATE="python3 .countersign/countersign.py"
FILE="${COUNTERSIGN_DEMO_FILE:-src/sarif.ts}"
OTHER="${COUNTERSIGN_DEMO_OTHER:-src/report.ts}"
cd "$WS" || exit 1

say() { printf '\n== %s ==\n' "$1"; }

say "task A opens and observes $FILE"
printf '{"event":"SessionStart","session_id":"task_A"}' | $GATE session-start
printf '{"event":"PostToolUse","session_id":"task_A","tool":"read_file","input":{"path":"%s"}}' "$FILE" | $GATE record

say "task B opens, observes $OTHER, then rewrites $FILE for real"
printf '{"event":"SessionStart","session_id":"task_B"}' | $GATE session-start
printf '{"event":"PostToolUse","session_id":"task_B","tool":"read_file","input":{"path":"%s"}}' "$OTHER" | $GATE record
python3 -c "p='$FILE';t=open(p).read();open(p,'w').write(t+'\n// rewritten by task B\n');print('$FILE rewritten by task B')"

say "task A resumes and proposes an edit to the file that changed"
printf '{"event":"PreToolUse","session_id":"task_A","tool":"write_file","input":{"path":"%s","content":"// refactor"}}' "$FILE" | $GATE check
printf 'exit=%s\n' "$?"

say "task A proposes an edit to a file only task B has observed"
printf '{"event":"PreToolUse","session_id":"task_A","tool":"write_file","input":{"path":"%s","content":"// x"}}' "$OTHER" | $GATE check
printf 'exit=%s\n' "$?"

say "recovery: fresh task, re-observe, the same edit is admitted"
printf '{"event":"SessionStart","session_id":"task_A2"}' | $GATE session-start
printf '{"event":"PostToolUse","session_id":"task_A2","tool":"read_file","input":{"path":"%s"}}' "$FILE" | $GATE record
printf '{"event":"PreToolUse","session_id":"task_A2","tool":"write_file","input":{"path":"%s","content":"// refactor"}}' "$FILE" | $GATE check
printf 'exit=%s\n' "$?"

say "event log"
cat .countersign/events.jsonl
