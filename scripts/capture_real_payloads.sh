#!/bin/sh
# Capture the runtime's real hook payloads into a workspace without ever blocking.
# Usage: sh capture_real_payloads.sh /path/to/workspace [gate path]
set -eu
WS="${1:?usage: capture_real_payloads.sh /path/to/workspace}"
GATE="${2:-$HOME/.local/share/countersign/countersign.py}"
mkdir -p "$WS/.bob" "$WS/.countersign"
python3 - "$WS" "$GATE" <<'PY'
import json, os, sys
ws, gate = sys.argv[1], sys.argv[2]
hooks = {ev: [{"hooks": [{"type": "command",
          "command": f"COUNTERSIGN_WORKSPACE={ws} python3 {gate} probe", "timeout": 10}]}]
         for ev in ("SessionStart", "PostToolUse", "PreToolUse")}
json.dump({"hooks": hooks}, open(os.path.join(ws, ".bob", "settings.json"), "w"), indent=2)
print("probe hooks written; run one task, then inspect", os.path.join(ws, ".countersign", "payloads"))
PY
