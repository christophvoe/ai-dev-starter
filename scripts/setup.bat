@echo off
title Project Setup
echo ============================================================
echo   One-Time Project Setup
echo ============================================================
echo.

cd /d "%~dp0.."

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo Copying .env.example to .env...
if not exist ".env" (
    copy ".env.example" ".env"
    echo DONE: Edit .env and fill in your API keys!
) else (
    echo SKIPPED: .env already exists
)

echo.
echo ============================================================
echo   Setup complete!
echo   Next: Edit .env with your API keys, then open VS Code
echo   VS Code will auto-activate the venv in every terminal
echo ============================================================
echo.
pause
