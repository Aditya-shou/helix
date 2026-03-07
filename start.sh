#!/usr/bin/env bash
# start.sh — Start Helix and open it in the browser.
# Run once: chmod +x start.sh
# Then just double-click the .desktop file or run ./start.sh

set -e

HELIX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HELIX_DIR/.logs"
VENV="$HELIX_DIR/venv"
FRONTEND="$HELIX_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173
URL="http://localhost:$FRONTEND_PORT"

mkdir -p "$LOG_DIR"

# Activate venv
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
else
    echo "[Helix] ERROR: venv not found at $VENV"
    echo "        Run: python -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Kill any leftover processes on these ports
kill_port() {
    local port=$1
    local pid
    pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "[Helix] Clearing port $port (pid $pid)"
        kill "$pid" 2>/dev/null || true
        sleep 0.5
    fi
}

kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Write PIDs so stop.sh can clean up
PID_FILE="$LOG_DIR/helix.pids"
> "$PID_FILE"

# Start FastAPI backend
echo "[Helix] Starting backend on port $BACKEND_PORT..."
cd "$HELIX_DIR"
uvicorn backend.api:app --port $BACKEND_PORT \
    --log-level warning \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" >> "$PID_FILE"

# Wait for backend to be ready
for i in {1..20}; do
    if curl -sf "http://localhost:$BACKEND_PORT/api/projects" > /dev/null 2>&1; then
        echo "[Helix] Backend ready."
        break
    fi
    sleep 0.5
done

# Build or serve frontend
# If a production build exists, serve it statically (faster, no node needed).
# Otherwise fall back to vite dev server.
DIST="$FRONTEND/dist"

if [ -d "$DIST" ]; then
    echo "[Helix] Serving built frontend..."
    cd "$HELIX_DIR"
    python -m http.server $FRONTEND_PORT --directory "$DIST" \
        > "$LOG_DIR/frontend.log" 2>&1 &
else
    echo "[Helix] Starting Vite dev server..."
    cd "$FRONTEND"
    npm run dev -- --port $FRONTEND_PORT \
        > "$LOG_DIR/frontend.log" 2>&1 &
fi

FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"

# Wait for frontend to be ready
echo "[Helix] Waiting for frontend..."
for i in {1..30}; do
    if curl -sf "$URL" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Open browser
echo "[Helix] Opening $URL"
if command -v xdg-open &> /dev/null; then
    xdg-open "$URL" &
elif command -v firefox &> /dev/null; then
    firefox "$URL" &
fi

echo "[Helix] Running. To stop: ./stop.sh"
echo "[Helix] Logs: $LOG_DIR/"
