#!/bin/sh
# Start the whole product: the runtime, then the console that reads it.
#
#   sh run.sh                 runtime + console
#   sh run.sh --runtime-only  runtime only
#   COUNTERSIGN_WORKSPACE=/path/to/repo sh run.sh
#
# The runtime holds no state of its own: it reads the store the gate writes in the
# repository under control and measures git and the filesystem directly.
#
# The console is served from a production build. It is not started in dev mode: a dev
# server blocks its own dev resources when the page is opened on 127.0.0.1, which leaves
# the page rendered but never hydrated, and a console that looks alive while showing
# nothing is worse than one that refuses to start. If the port is taken, this says so
# instead of quietly degrading.
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${COUNTERSIGN_PORT:-4319}"
CONSOLE_PORT="${PORT_CONSOLE:-4311}"
LOG="$ROOT/.countersign-runtime.log"
CONSOLE_LOG="$ROOT/.countersign-console.log"

echo "countersign"
echo "  gate      $ROOT/countersign.py"
echo "  runtime   http://127.0.0.1:$PORT"
echo "  console   http://127.0.0.1:$CONSOLE_PORT/console"
echo

if curl -sf "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then
  echo "a runtime is already answering on $PORT; using it"
else
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
fi

if [ "${1:-}" = "--runtime-only" ]; then
  echo "runtime only; press ctrl-c to stop"
  wait "${RUNTIME_PID:-}" 2>/dev/null || true
  exit 0
fi

if [ ! -d "$ROOT/landing/node_modules" ]; then
  echo "installing console dependencies (first run only)"
  (cd "$ROOT/landing" && npm install --silent)
fi

cd "$ROOT/landing"
if [ ! -f .next/BUILD_ID ]; then
  echo "building the console (first run, or after a clean)"
  npm run build >/dev/null
fi

if curl -sf "http://127.0.0.1:$CONSOLE_PORT/console" >/dev/null 2>&1; then
  echo "a console is already answering on $CONSOLE_PORT; using it"
  exit 0
fi

echo "starting console on $CONSOLE_PORT (log $CONSOLE_LOG)"
PORT="$CONSOLE_PORT" npm run start >"$CONSOLE_LOG" 2>&1 &
CONSOLE_PID=$!
trap 'kill ${RUNTIME_PID:-} ${CONSOLE_PID:-} 2>/dev/null || true' INT TERM

i=0
until curl -sf "http://127.0.0.1:$CONSOLE_PORT/console" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then
    echo "console did not answer on $CONSOLE_PORT; last lines of $CONSOLE_LOG:"
    tail -20 "$CONSOLE_LOG"
    echo "if the port is held by another process, stop it or set PORT_CONSOLE"
    exit 1
  fi
  sleep 0.5
done
echo "console ready (pid $CONSOLE_PID)"
echo
echo "open http://127.0.0.1:$CONSOLE_PORT/console ; press ctrl-c to stop both"
wait "${CONSOLE_PID:-}"
