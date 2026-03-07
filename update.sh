#!/usr/bin/env bash
# update.sh — Rebuild and restart Helix after making changes.
#
# Usage:
#   ./update.sh          — rebuild frontend + restart everything
#   ./update.sh --fe     — frontend only (rebuild + restart)
#   ./update.sh --be     — backend only (just restart, no build needed)
#   ./update.sh --deps   — reinstall Python + Node dependencies then restart

set -e

HELIX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HELIX_DIR/venv"
FRONTEND="$HELIX_DIR/frontend"
MODE="${1:-}"

echo "[Helix] Updating..."

#  Stop running instance
if [ -f "$HELIX_DIR/.logs/helix.pids" ]; then
    bash "$HELIX_DIR/stop.sh"
    sleep 1
fi

#  Activate venv
source "$VENV/bin/activate"

#  Dependency reinstall
if [ "$MODE" = "--deps" ]; then
    echo "[Helix] Reinstalling Python dependencies..."
    pip install -r "$HELIX_DIR/requirements.txt" --quiet

    echo "[Helix] Reinstalling Node dependencies..."
    cd "$FRONTEND" && npm install --silent && cd "$HELIX_DIR"
fi

# Frontend rebuild
if [ "$MODE" != "--be" ]; then
    echo "[Helix] Building frontend..."
    cd "$FRONTEND"
    npm run build
    echo "[Helix] Frontend built → frontend/dist/"
    cd "$HELIX_DIR"
fi

#  Restart
echo "[Helix] Restarting..."
bash "$HELIX_DIR/start.sh"
