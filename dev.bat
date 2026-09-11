@echo off
cd /d D:\AI_Agent

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Jarvis virtual environment not found.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo ==========================================
echo   JARVIS V2 DEVELOPMENT TERMINAL
echo ==========================================
echo Project: %CD%
echo.

cmd /k