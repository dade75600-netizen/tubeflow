@echo off
cd /d "%~dp0"
echo ===================================================
echo Starting TubeFlow YouTube Automation Dashboard...
echo ===================================================
if not exist .venv\Scripts\activate.bat (
    echo Error: Virtual environment (.venv) not found.
    echo Please make sure you have run the setup and created .venv.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause