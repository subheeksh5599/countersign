#!/bin/sh
# DEMO HARNESS: stands in for a second task writing a path shortly after another
# task read it. Backgrounded with a delay so the write lands inside the window
# between the observation and the edit, whatever order the runtime runs hooks in.
# Usage: sh concurrent_writer.sh /path/to/file [delay-seconds]
F="$1"
( sleep "${2:-4}"; printf '\n// rewritten by a concurrent task inside the read->write window\n' >> "$F" ) &
