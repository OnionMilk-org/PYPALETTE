@echo off
REM PyPalette Compilation Script
REM Compiles the modular PyPalette application into a standalone EXE

echo ==========================================
echo PyPalette - Standalone EXE Compilation
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

REM Check if PyInstaller is installed
echo Checking for PyInstaller...
"C:\Program Files\Python312\python.exe" -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Installing PyInstaller...
    "C:\Program Files\Python312\python.exe" -m pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo Failed to install PyInstaller!
        pause
        exit /b 1
    )
)

REM Create build directory if it doesn't exist
if not exist "build" (
    echo Creating build directory...
    mkdir build
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build\PyPalette.exe" del "build\PyPalette.exe"
if exist "build\PyPalette" rmdir /s /q "build\PyPalette"
if exist "PyPalette.spec" del "PyPalette.spec"

echo.
echo Starting compilation...
echo This may take several minutes...
echo.

REM Check if icon file exists
set ICON_PARAM=
if exist "icon.ico" (
    echo Using custom icon: icon.ico
    set ICON_PARAM=--icon=icon.ico
) else (
    echo No custom icon found, using default
)

REM Compile the application
"C:\Program Files\Python312\python.exe" -m PyInstaller ^
    --name PyPalette ^
    --onefile ^
    --windowed ^
    --distpath build ^
    --workpath build ^
    --specpath build ^
    %ICON_PARAM% ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import numpy ^
    --hidden-import PyQt5 ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtCore ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ==========================================
    echo Compilation FAILED!
    echo ==========================================
    echo Check the error messages above.
    echo Common issues:
    echo - Missing dependencies (run: install_requirements.bat)
    echo - Module import errors (check --hidden-import parameters)
    echo - Insufficient disk space (need ~200MB free)
    echo - Permission issues (try running as Administrator)
    
    REM Check if EXE was still created despite errors
    if exist "build\PyPalette.exe" (
        echo.
        echo WARNING: Compilation had errors but EXE was created!
        echo Check if the application works correctly.
        goto success
    )
    
    pause
    exit /b 1
)

REM Check if the EXE was created successfully
:success
if exist "build\PyPalette.exe" (
    echo.
    echo ==========================================
    echo Compilation SUCCESSFUL!
    echo ==========================================
    echo.
    echo Standalone executable created: build\PyPalette.exe
    echo.
    echo File size:
    for %%A in ("build\PyPalette.exe") do echo   %%~zA bytes
    echo.
    echo You can now distribute this single EXE file!
    echo The EXE includes all dependencies and doesn't require Python to be installed.
    echo.
    echo Note: First run might be slower as it extracts files to temp directory.
    echo.
) else (
    echo.
    echo ==========================================
    echo Compilation completed but EXE not found!
    echo ==========================================
    echo Check build directory for any generated files.
)

REM Clean up temporary files
echo Cleaning up temporary files...
if exist "build\temp" rmdir /s /q "build\temp"

echo.
echo Build process completed.
echo Press any key to exit...
pause >nul