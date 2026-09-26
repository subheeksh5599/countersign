#!/bin/sh
# Regenerate the evidence page and serve it locally.
# Usage: sh serve_lens.sh /path/to/workspace [port]
set -eu
WS="${1:?usage: serve_lens.sh /path/to/workspace [port]}"
PORT="${2:-8080}"
python3 "$(dirname "$0")/../lens.py" "$WS" -o "$WS/lens.html"
echo "serving $WS/lens.html on http://127.0.0.1:$PORT"
cd "$WS" && python3 -m http.server "$PORT"
