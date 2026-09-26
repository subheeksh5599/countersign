#!/bin/sh
# The live scene: one task reads a file, a concurrent writer changes it inside the
# read -> write window, the edit is refused. Usage: sh live_two_task_demo.sh /path/to/workspace
set -eu
WS="${1:?usage: live_two_task_demo.sh /path/to/workspace}"
GATE="python3 $WS/.countersign/countersign.py"
FILE="$WS/pricing.ts"

cat > "$WS/.countersign/concurrent_writer.sh" <<'EOS'
#!/bin/sh
# stands in for a second task writing the path; backgrounded so the write lands
# inside the window regardless of hook ordering
F="$1"
( sleep "${2:-4}"; printf '\n// rewritten by a concurrent task inside the read->write window\n' >> "$F" ) &
EOS
chmod +x "$WS/.countersign/concurrent_writer.sh"

python3 - "$WS" "$GATE" <<'PY'
import json, os, sys
ws, gate = sys.argv[1], sys.argv[2]
env = f"COUNTERSIGN_WORKSPACE={ws}"
hooks = {
  "SessionStart": [{"hooks": [{"type": "command", "command": f"{env} {gate} session-start", "timeout": 10}]}],
  "PostToolUse": [
    {"matcher": "^(read_file)$", "hooks": [{"type": "command", "command": f"{env} {gate} record", "timeout": 10}]},
    {"matcher": "^read_file$", "hooks": [{"type": "command", "command": f"sh {ws}/.countersign/concurrent_writer.sh {ws}/pricing.ts", "timeout": 10}]}],
  "PreToolUse": [{"matcher": ".*(apply_diff|write_file|search_and_replace|delete).*",
                  "hooks": [{"type": "command", "command": f"{env} {gate} check", "timeout": 10}]}]}
json.dump({"hooks": hooks}, open(os.path.join(ws, ".bob", "settings.json"), "w"), indent=2)
print("hooks installed; now run one task that reads and then edits", os.path.basename(ws))
PY
