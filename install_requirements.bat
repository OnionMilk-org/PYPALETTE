@echo off
REM Install PyPalette Requirements
REM Installs all dependencies needed for PyPalette

echo ==========================================
echo PyPalette - Installing Requirements
echo ==========================================

REM Change to the script directory
cd /d "%~dp0"

REM Check if Python is available
"C:\Program Files\Python312\python.exe" --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found at "C:\Program Files\Python312\python.exe"
    echo Please install Python or update the path in this script.
    pause
    exit /b 1
)

echo Installing requirements from requirements.txt...
echo.

"C:\Program Files\Python312\python.exe" -m pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo ==========================================
    echo Installation FAILED!
    echo ==========================================
    echo Please check your internet connection and try again.
    echo You may also try installing packages individually:
    echo   pip install numpy pillow PyQt5 pyinstaller
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Installation SUCCESSFUL!
echo ==========================================
echo.
echo All requirements have been installed.
echo You can now run PyPalette or compile it to EXE.
echo.
echo Next steps:
echo   - Run application: start_palette_editor.bat
echo   - Compile to EXE: compile.bat
echo.
pause