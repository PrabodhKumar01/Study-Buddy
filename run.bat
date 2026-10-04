@echo off
setlocal
echo ===================================================
echo           Starting Study Buddy (Offline Mode)
echo ===================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Setup virtual environment if missing
if not exist "venv" (
    echo [1/3] Creating virtual environment (venv)...
    python -m venv venv
)

echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing / verifying requirements...
pip install -r requirements.txt --quiet

echo [3/3] Launching Study Buddy server...
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
