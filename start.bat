@echo off
title MirrorGrid Phase 5
color 0B
echo.
echo  ╔══════════════════════════════════╗
echo  ║     MirrorGrid Phase 5           ║
echo  ║     localhost:8000               ║
echo  ╚══════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause
    exit /b
)

:: Install deps if needed
echo  [1/2] Checking dependencies...
pip install -r requirements.txt -q

echo  [2/2] Starting server...
echo.
echo  Open your browser: http://localhost:8000
echo  Press Ctrl+C to stop.
echo.

python server.py
pause
