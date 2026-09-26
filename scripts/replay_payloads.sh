#!/bin/sh
# Replay captured payloads through the gate for a given workspace.
# Usage: sh replay_payloads.sh /path/to/workspace [fixtures.json]
set -eu
WS="${1:?usage: replay_payloads.sh /path/to/workspace [fixtures.json]}"
FIX="${2:-$(dirname "$0")/../tests/fixtures/real_payloads.json}"
python3 - "$WS" "$FIX" <<'PY'
import json, os, subprocess, sys
ws, fix = sys.argv[1], sys.argv[2]
gate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countersign.py")
payloads = json.load(open(fix))
env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
for name in sorted(payloads):
    p = payloads[name]
    ev = p.get("hook_event_name", "")
    mode = {"SessionStart": "session-start", "PostToolUse": "record",
            "PreToolUse": "check"}.get(ev)
    if not mode:
        continue
    r = subprocess.run([sys.executable, gate, mode], input=json.dumps(p),
                       capture_output=True, text=True, env=env, cwd=ws)
    print(f"{name} {ev} -> exit {r.returncode}")
PY
