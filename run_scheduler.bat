@echo off
cd /d "%~dp0"
echo ===================================================
echo Starting TubeFlow YouTube Background Scheduler...
echo ===================================================
if not exist .venv\Scripts\activate.bat (
    echo Error: Virtual environment (.venv) not found.
    echo Please make sure you have run the setup and created .venv.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python -m backend.scheduler
pause
