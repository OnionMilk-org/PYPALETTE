@echo off
REM Dynamic Palette Editor Launcher
REM This script starts the PyQt5 Palette Editor application

echo Starting Dynamic Palette Editor...

REM Change to the script directory
cd /d "%~dp0"

REM Start the Python application
"C:\Program Files\Python312\python.exe" main.py

REM Keep the window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo.
    echo Program exited with error code: %ERRORLEVEL%
    echo Press any key to close this window...
)