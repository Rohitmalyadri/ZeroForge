#!/usr/bin/env bash
# ZeroForge Unix Launcher (macOS / Linux)

set -e

# Change directory to the ZeroForge project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect Python interpreter
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo ""
    echo "============================================================"
    echo "ZeroForge could not find Python."
    echo "============================================================"
    echo ""
    echo "Please install Python 3.x and make sure"
    echo "Python is available in your PATH."
    echo ""
    echo "Then run ZeroForge again."
    echo ""
    exit 1
fi

exec "$PY_CMD" -m zeroforge "$@"
