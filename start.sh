#!/bin/bash

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║     MirrorGrid Phase 5           ║"
echo "  ║     localhost:8000               ║"
echo "  ╚══════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  [ERROR] Python3 not found."
    exit 1
fi

echo "  [1/2] Installing dependencies..."
pip3 install -r requirements.txt -q

echo "  [2/2] Starting server..."
echo ""
echo "  Open browser: http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo ""

python3 server.py
