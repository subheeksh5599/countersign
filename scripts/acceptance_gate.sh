#!/bin/sh
# Acceptance run for the gate itself, using the real hook command as a subprocess.
# No runtime, no dashboard: this proves the mechanism on a fresh repository.
set -u
WS="${1:-/tmp/csign_accept}"
GATE="$(cd "$(dirname "$0")/.." && pwd)/countersign.py"
rm -rf "$WS"; mkdir -p "$WS"; cd "$WS"
git init -q .; git config user.email a@a; git config user.name a
mkdir -p src
printf 'export const refund = 1\n' > src/payment-refund.ts
printf 'export const RETRY_LIMIT = 3\n' > src/config.ts
git add -A; git commit -qm "initial"

say() { printf '\n== %s ==\n' "$1"; }
hook() {  # hook MODE JSON  -> prints exit code
  printf '%s' "$2" | COUNTERSIGN_WORKSPACE="$WS" python3 "$GATE" "$1"
  printf 'exit=%s\n' "$?"
}

SID="session_acceptance"
say "1. start a session"
hook session-start "{\"hook_event_name\":\"SessionStart\",\"session_id\":\"$SID\",\"cwd\":\"$WS\"}" | tail -1

say "2. the agent reads the config file (evidence recorded)"
hook record "{\"hook_event_name\":\"PostToolUse\",\"session_id\":\"$SID\",\"tool_name\":\"read_file\",\"cwd\":\"$WS\",\"tool_input\":{\"path\":\"$WS/src/config.ts\"}}" | tail -1
HELD=$(python3 -c "
import json;m=json.load(open('$WS/.countersign/tasks/$SID.json'))
print(m['files']['src/config.ts']['digest'])")
echo "held digest: ${HELD%????????????????????????????????????????????????????}..."

say "3. an external process changes that file"
printf 'export const RETRY_LIMIT = 99\n' > src/config.ts
NOW=$(python3 -c "import hashlib;print(hashlib.sha256(open('$WS/src/config.ts','rb').read()).hexdigest())")
echo "disk digest: ${NOW%????????????????????????????????????????????????????}..."

say "4. the agent attempts a real state-changing call"
hook check "{\"hook_event_name\":\"PreToolUse\",\"session_id\":\"$SID\",\"tool_name\":\"apply_diff\",\"cwd\":\"$WS\",\"tool_input\":{\"path\":\"$WS/src/config.ts\",\"diff\":\"<<<<<<< SEARCH\\n-export const RETRY_LIMIT = 99\\n=======\\n+export const RETRY_LIMIT = 5\\n>>>>>>> REPLACE\"}}"

say "5. the receipt written for that refusal"
python3 - "$WS" <<'PY'
import glob, json, os, sys
ws = sys.argv[1]
f = sorted(glob.glob(os.path.join(ws, '.countersign', 'receipts', '*.json')))[-1]
r = json.load(open(f))
print("file:", os.path.basename(f))
for k in ("receipt_id", "timestamp", "session_id", "repository", "branch", "git_head",
          "tool_name", "tool_classification", "classification_reason", "tool_arguments_hash",
          "affected_paths", "evidence_hashes", "current_hashes", "verdict", "reason_code",
          "exit_code", "runtime_latency_ms", "previous_receipt_hash"):
    v = r.get(k)
    if isinstance(v, str) and len(v) > 24:
        v = v[:24] + "..."
    print(f"  {k}: {v}")
print("  tool_arguments:", json.dumps(r.get("tool_arguments"))[:120])
PY

say "6. recover: refresh the evidence this task holds"
hook refresh "{\"hook_event_name\":\"PostToolUse\",\"session_id\":\"$SID\",\"cwd\":\"$WS\",\"tool_input\":{}}" | tail -1

say "7. retry the same operation"
hook check "{\"hook_event_name\":\"PreToolUse\",\"session_id\":\"$SID\",\"tool_name\":\"apply_diff\",\"cwd\":\"$WS\",\"tool_input\":{\"path\":\"$WS/src/config.ts\"}}" | tail -2

say "8. the receipt chain"
python3 - "$WS" <<'PY'
import glob, json, os, sys
ws = sys.argv[1]
files = sorted(glob.glob(os.path.join(ws, '.countersign', 'receipts', '*.json')))
prev = None
for f in files:
    r = json.load(open(f))
    body = {k: v for k, v in r.items() if k != 'receipt_hash'}
    import hashlib
    recomputed = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    print(f"{r['receipt_id']}  verdict={r['verdict']:<8} exit={r['exit_code']} "
          f"prev={(r['previous_receipt_hash'] or 'none')[:12]}  verify={'valid' if recomputed == r['receipt_hash'] else 'INVALID'}")
    if prev is not None and r['previous_receipt_hash'] != prev:
        print("  chain break")
    prev = r['receipt_hash']
PY
echo
echo "== files on disk after the whole flow =="
ls "$WS/.countersign/receipts" | tr '\n' ' '; echo
cat src/config.ts
