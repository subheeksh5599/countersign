#!/bin/sh
# Start the whole product: the runtime, then the console that reads it.
#
#   sh run.sh                 runtime + console
#   sh run.sh --runtime-only  runtime only
#   COUNTERSIGN_WORKSPACE=/path/to/repo sh run.sh
#
# The runtime holds no state of its own: it reads the store the gate writes in the
# repository under control and measures git and the filesystem directly.
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${COUNTERSIGN_PORT:-4319}"
CONSOLE_PORT="${PORT_CONSOLE:-4311}"
LOG="$ROOT/.countersign-runtime.log"

echo "countersign"
echo "  gate      $ROOT/countersign.py"
echo "  runtime   http://127.0.0.1:$PORT"
echo "  console   http://127.0.0.1:$CONSOLE_PORT/console"
echo

python3 "$ROOT/runtime/countersign_runtime.py" >"$LOG" 2>&1 &
RUNTIME_PID=$!
trap 'kill $RUNTIME_PID 2>/dev/null || true' INT TERM

i=0
until curl -sf "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 40 ]; then
    echo "runtime did not answer; last lines of $LOG:"
    tail -20 "$LOG"
    exit 1
  fi
  sleep 0.25
done
echo "runtime ready (pid $RUNTIME_PID, log $LOG)"

if [ "${1:-}" = "--runtime-only" ]; then
  echo "runtime only; press ctrl-c to stop"
  wait $RUNTIME_PID
  exit 0
fi

if [ ! -d "$ROOT/landing/node_modules" ]; then
  echo "installing console dependencies (first run only)"
  (cd "$ROOT/landing" && npm install --silent)
fi

echo "starting console on $CONSOLE_PORT"
cd "$ROOT/landing"
PORT="$CONSOLE_PORT" npm run start 2>/dev/null || PORT="$CONSOLE_PORT" npm run dev
