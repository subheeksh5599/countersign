#!/bin/sh
# Scene: the workspace revision moves under a task, and the file on disk looks
# exactly like the file the task read.
#
# This is the case the digest alone cannot see: same bytes, different history. A
# rebase, an amend, or a restore to an earlier blob all produce it. The gate refuses
# it as REVISION_MOVED.
#
# Usage: sh scene_revision_moved.sh [workspace]
set -u
WS="${1:-/tmp/cs_revision}"
GATE_SRC="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$WS"; mkdir -p "$WS"
cd "$WS"
git init -q .; git config user.email a@a; git config user.name a
printf 'export const rate = 1\n' > pricing.ts
git add -A; git commit -qm "initial"

cd "$GATE_SRC" && sh install.sh "$WS" --write >/dev/null
cd "$WS" || exit 1
GATE="$WS/.countersign/countersign.py"
SID="task_revision"
P="$WS/pricing.ts"

say() { printf '\n== %s ==\n' "$1"; }
run() {
  printf '%s' "$2" | env COUNTERSIGN_WORKSPACE="$WS" python3 "$GATE" "$1"
  printf 'exit=%s\n' "$?"
}

say "task opens and reads pricing.ts (rate = 1)"
run session-start "{\"hook_event_name\":\"SessionStart\",\"session_id\":\"$SID\",\"cwd\":\"$WS\"}" >/dev/null
run record "{\"hook_event_name\":\"PostToolUse\",\"session_id\":\"$SID\",\"tool_name\":\"read_file\",\"cwd\":\"$WS\",\"tool_input\":{\"path\":\"$P\"}}" | tail -2
DIGEST_AT_READ=$(sha256sum "$P" | cut -c1-12)
REV_AT_READ=$(git rev-parse "HEAD:pricing.ts" | cut -c1-12)
echo "digest at read: $DIGEST_AT_READ   revision at read: $REV_AT_READ"

say "another actor commits a different rate to that path"
printf 'export const rate = 9\n' > "$P"
git add -A; git commit -qm "another actor changes the rate"
REV_AFTER=$(git rev-parse "HEAD:pricing.ts" | cut -c1-12)
echo "revision now:   $REV_AFTER"

say "the working file is restored to the exact bytes the task read"
git show "HEAD~1:pricing.ts" > "$P"
git checkout -q -- . 2>/dev/null || true
git show "HEAD~1:pricing.ts" > "$P"
DIGEST_NOW=$(sha256sum "$P" | cut -c1-12)
echo "digest now:     $DIGEST_NOW"
[ "$DIGEST_NOW" = "$DIGEST_AT_READ" ] && echo "the file on disk is byte-identical to what the task read"

say "the task tries to edit"
run check "{\"hook_event_name\":\"PreToolUse\",\"session_id\":\"$SID\",\"cwd\":\"$WS\",\"tool_name\":\"apply_diff\",\"tool_input\":{\"path\":\"$P\"}}" | tail -6

say "the file on disk did not change"
cat "$P"
printf '\nA digest comparison alone would have admitted this edit. Both digests match;\n'
printf 'only the committed revision for that path moved, and that is the difference the\n'
printf 'gate refuses on.\n'
