#!/bin/bash

# Sovereign-Mind 3.0 - Linux Launcher
# "One-Click" Experience for Linux

echo -e "\033[0;36m========================================\033[0m"
echo -e "\033[0;36m   SOVEREIGN-MIND 3.0 - LAUNCHER        \033[0m"
echo -e "\033[0;36m========================================\033[0m"

# 1. Check Dependencies
command -v python3 >/dev/null 2>&1 || { echo >&2 "[ERROR] python3 is required but not installed. Aborting."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo >&2 "[ERROR] npm is required but not installed. Aborting."; exit 1; }

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo -e "\033[0;33m[*] Creating Python virtual environment...\033[0m"
    python3 -m venv venv
fi

source venv/bin/activate
echo -e "\033[0;32m[*] Virtual environment activated.\033[0m"

# 3. Install Requirements
echo -e "\033[0;33m[*] Checking dependencies...\033[0m"
pip install -e . > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m[ERROR] Failed to install requirements.\033[0m"
    exit 1
fi

# 4. Download Model
echo -e "\033[0;32m[*] Verifying AI Engine...\033[0m"
python3 scripts/download_model.py
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m[ERROR] Model download failed.\033[0m"
    exit 1
fi

# 5. Start Backend
echo -e "\033[0;32m[*] Starting Sovereign-Mind Backend...\033[0m"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 6. Start Frontend
echo -e "\033[0;32m[*] Starting Dashboard UI...\033[0m"
cd ui
if [ ! -d "node_modules" ]; then
    echo -e "\033[0;33m[*] Installing UI dependencies...\033[0m"
    npm install > /dev/null 2>&1
fi
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# 7. Wait and Clean Up on Exit
echo -e "\033[0;36m[*] Systems Nominal.\033[0m"
echo "    > Backend: http://localhost:8000/docs"
echo "    > Frontend: http://localhost:3001"
echo "    > Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

wait
