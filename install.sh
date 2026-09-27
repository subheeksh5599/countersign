#!/bin/sh
# Install the gate.
#
#   sh install.sh --global                 machine-wide: gate, CLI wrapper, global hooks
#   sh install.sh /path/to/workspace       print the hook block for that workspace
#   sh install.sh /path/to/workspace --write   merge the block into the workspace
#
# Machine-wide install puts the gate under $COUNTERSIGN_HOME (default
# ~/.local/share/countersign), a `countersign` wrapper on the PATH, and merges the
# global hook block into ~/.bob/settings/settings.json with the gate path resolved.
# It is idempotent: existing blocks are not duplicated.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--global" ]; then
  DEST="${COUNTERSIGN_HOME:-$HOME/.local/share/countersign}"
  mkdir -p "$DEST" "$HOME/.local/bin"
  cp -f "$HERE/countersign.py" "$DEST/countersign.py"
  cp -f "$HERE/lens.py" "$DEST/lens.py"
  cp -f "$HERE/hooks-global.json" "$DEST/hooks-global.json"
  printf '#!/bin/sh\nexec python3 "%s/countersign.py" "$@"\n' "$DEST" > "$HOME/.local/bin/countersign"
  chmod +x "$HOME/.local/bin/countersign"
  python3 - "$DEST" <<'PY'
import json, os, sys
dest = sys.argv[1]
gate = os.path.join(dest, "countersign.py")
path = os.path.expanduser("~/.bob/settings/settings.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
cur = json.load(open(path)) if os.path.exists(path) else {}
add = json.load(open(os.path.join(dest, "hooks-global.json")))
existing = json.dumps(cur)
added = 0
for event, entries in add["hooks"].items():
    for e in entries:
        e = json.loads(json.dumps(e).replace("COUNTERSIGN_GATE", gate))
        if gate in json.dumps(e) and gate in existing:
            continue
        cur.setdefault("hooks", {}).setdefault(event, []).append(e)
        added += 1
json.dump(cur, open(path, "w"), indent=2)
print(f"gate installed at {gate}")
print(f"wrapper at {os.path.expanduser('~/.local/bin/countersign')}")
print(f"global hook block: {added} entr(y/ies) added to {path}")
PY
  echo "set COUNTERSIGN_WORKSPACE before running, or export it in your shell profile"
  exit 0
fi

WS="${1:?usage: sh install.sh /path/to/workspace [--write] | sh install.sh --global}"
MODE="${2:---print}"
mkdir -p "$WS/.countersign"
cp -f "$HERE/countersign.py" "$WS/.countersign/countersign.py"
cp -f "$HERE/hooks.json" "$WS/.countersign/hooks.json"

if [ "$MODE" != "--write" ]; then
  echo "would merge into $WS/.bob/settings.json:"
  cat "$WS/.countersign/hooks.json"
  exit 0
fi

python3 - "$WS" <<'PY'
import json, os, sys
ws = sys.argv[1]
# If a machine-wide block is already installed, this workspace block makes two gates
# observe the same call: two checks, two receipts. Say so rather than let it surprise
# an operator reading the receipt log.
g = os.path.expanduser("~/.bob/settings/settings.json")
if os.path.exists(g) and "countersign" in open(g, encoding="utf-8").read():
    print("warning: ~/.bob/settings/settings.json already has a countersign hook block.")
    print("         with this workspace block as well, every state-changing call is")
    print("         checked twice and writes two receipts. install one, not both.")
path = os.path.join(ws, ".bob", "settings.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
cur = json.load(open(path)) if os.path.exists(path) else {}
add = json.load(open(os.path.join(ws, ".countersign", "hooks.json")))
added = 0
for event, entries in add["hooks"].items():
    bucket = cur.setdefault("hooks", {}).setdefault(event, [])
    have = {json.dumps(x, sort_keys=True) for x in bucket}
    for e in entries:
        k = json.dumps(e, sort_keys=True)
        if k in have:
            continue
        bucket.append(e)
        have.add(k)
        added += 1
json.dump(cur, open(path, "w"), indent=2)
print(f"merged into {path} | entries added: {added} | "
      f"totals: { {k: len(v) for k, v in cur['hooks'].items()} }")
PY
