#!/usr/bin/env bash
# stop.sh — Cleanly shut down Helix.

HELIX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$HELIX_DIR/.logs/helix.pids"

if [ ! -f "$PID_FILE" ]; then
    echo "[Helix] No running instance found."
    exit 0
fi

echo "[Helix] Stopping..."

while IFS= read -r pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null && echo "[Helix] Stopped pid $pid"
    fi
done < "$PID_FILE"

rm -f "$PID_FILE"

# Belt-and-suspenders: kill by port too
for port in 8000 5173; do
    pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
    fi
done

echo "[Helix] Stopped."
