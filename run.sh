#!/usr/bin/env bash
set -e

echo "==================================================="
echo "          Starting Study Buddy (Offline Mode)"
echo "==================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in your PATH."
    exit 1
fi

# Setup virtual environment if missing
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment (venv)..."
    python3 -m venv venv
fi

echo "[2/3] Activating virtual environment..."
source venv/bin/activate

echo "Installing / verifying requirements..."
pip install -r requirements.txt -q

echo "[3/3] Launching Study Buddy at http://127.0.0.1:8000..."
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
