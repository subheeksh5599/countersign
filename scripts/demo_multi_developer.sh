#!/bin/sh
# Two developers, two clones, one repository, one gate.
#
# What it shows, including the part that is uncomfortable: a local gate cannot see
# a change that exists only on another machine. It sees it the moment the clone
# fetches the change. So the demo prints two verdicts for the same task:
#
#   before fetching: ADMITTED  (the clone's file really is unchanged)
#   after fetching:  REFUSED   (EVIDENCE_SUPERSEDED)
#
# Usage: sh demo_multi_developer.sh [workdir]
set -u
ROOT="${1:-/tmp/cs_multi}"
GATE_SRC="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$ROOT"; mkdir -p "$ROOT"

# ---- a bare remote and two clones -----------------------------------------
git init -q --bare "$ROOT/remote.git"
git clone -q "$ROOT/remote.git" "$ROOT/devA"
cd "$ROOT/devA"
git config user.email a@example.com; git config user.name dev-a
printf 'export const rate = 1\n' > pricing.ts
printf 'export const report = 1\n' > report.ts
git add -A; git commit -qm "initial"
git push -q origin master 2>/dev/null || git push -q origin HEAD

git clone -q "$ROOT/remote.git" "$ROOT/devB"
cd "$ROOT/devB"
git config user.email b@example.com; git config user.name dev-b

# ---- install the gate into developer A's clone ----------------------------
cd "$GATE_SRC" && sh install.sh "$ROOT/devA" --write >/dev/null
A="$ROOT/devA"; GATE="$A/.countersign/countersign.py"
SID="task_dev_a_pricing"

say() { printf '\n== %s ==\n' "$1"; }

run() {   # run(event-json) -> prints exit code and body
  printf '%s' "$2" | env COUNTERSIGN_WORKSPACE="$A" python3 "$GATE" "$1"
  printf 'exit=%s\n' "$?"
}

say "developer A: task opens and reads pricing.ts"
run session-start "{\"hook_event_name\":\"SessionStart\",\"session_id\":\"$SID\",\"cwd\":\"$A\"}" >/dev/null
run record "{\"hook_event_name\":\"PostToolUse\",\"session_id\":\"$SID\",\"tool_name\":\"read_file\",\"cwd\":\"$A\",\"tool_input\":{\"path\":\"$A/pricing.ts\"}}" | tail -2

say "developer B: edits and commits the same path, pushes"
cd "$ROOT/devB"
printf 'export const rate = 9\n' > pricing.ts
git add -A; git commit -qm "dev-b changes the rate"; git push -q origin HEAD

say "developer A's task tries to edit, before the clone knows anything"
cd "$A"
run check "{\"hook_event_name\":\"PreToolUse\",\"session_id\":\"$SID\",\"cwd\":\"$A\",\"tool_name\":\"apply_diff\",\"tool_input\":{\"path\":\"$A/pricing.ts\"}}" | tail -2

say "the clone fetches the change"
git fetch -q origin && git merge -q --ff-only origin/master 2>/dev/null || git pull -q --ff-only origin master 2>/dev/null
cat pricing.ts

say "the same task tries the same edit again"
run check "{\"hook_event_name\":\"PreToolUse\",\"session_id\":\"$SID\",\"cwd\":\"$A\",\"tool_name\":\"apply_diff\",\"tool_input\":{\"path\":\"$A/pricing.ts\"}}" | tail -3

say "what the record shows"
printf '{"hook_event_name":"Export","session_id":"all","cwd":"%s"}' "$A" \
  | env COUNTERSIGN_WORKSPACE="$A" python3 "$GATE" export | tail -1
python3 - "$A" <<'PY'
import glob, json, os, sys
ws = sys.argv[1]
for f in sorted(glob.glob(os.path.join(ws, ".countersign", "exports", "*.json"))):
    rec = json.load(open(f))
    print("record:", os.path.basename(f))
    print("  task:", rec.get("task"), "| opened on commit:", rec.get("commit"))
    print("  verdicts:", [(v.get("verdict"), v.get("codes")) for v in rec.get("verdicts", [])])
    print("  record hash:", rec.get("record_hash"))
PY

printf '\nHonest note: the first verdict was ADMITTED because the clone really had not\n'
printf 'changed. A local gate cannot referee a change that lives on another machine; it\n'
printf 'refuses the moment the clone has the change. That is what the exported receipt is\n'
printf 'for: the server-side half.\n'
