@echo off
title Push Template to GitHub
echo ============================================================
echo   Push ai-dev-starter Template to Your GitHub
echo ============================================================
echo.

cd /d "C:\Users\Voelt\ai-dev-starter"

echo Step 1: Initialize git repo...
git init
git add -A
git commit -m "Initial commit: AI dev starter template"

echo.
echo Step 2: Creating GitHub repo and pushing...
echo (You may be prompted to log in to GitHub)
echo.

REM GitHub CLI must be installed and authenticated
gh auth status 2>nul
if errorlevel 1 (
    echo Logging in to GitHub...
    gh auth login
)

gh repo create ai-dev-starter --public --description "Template for AI-assisted Python projects: Copilot, Claude Code, Cline, MCPs, n8n" --push --source .

echo.
echo ============================================================
echo   Done! Repo available at:
echo   https://github.com/christophvoe/ai-dev-starter
echo ============================================================
echo.
pause
