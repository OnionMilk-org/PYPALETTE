@echo off
REM Advanced PyPalette Compilation Script
REM Provides options for different compilation modes

echo ==========================================
echo PyPalette - Advanced EXE Compilation
echo ==========================================

REM Change to the script directory
cd /d "%~dp0"

echo.
echo Select compilation mode:
echo 1. Single EXE file (recommended for distribution)
echo 2. Directory with files (faster startup)
echo 3. Debug build (with console window)
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto onefile
if "%choice%"=="2" goto onedir
if "%choice%"=="3" goto debug
goto invalid

:onefile
set BUILD_TYPE=--onefile --windowed
set BUILD_NAME=PyPalette
set BUILD_DESC=Single EXE
goto compile

:onedir
set BUILD_TYPE=--onedir --windowed
set BUILD_NAME=PyPalette
set BUILD_DESC=Directory
goto compile

:debug
set BUILD_TYPE=--onefile --console
set BUILD_NAME=PyPalette_Debug
set BUILD_DESC=Debug Console
goto compile

:invalid
echo Invalid choice! Please run the script again.
pause
exit /b 1

:compile
echo.
echo Building: %BUILD_DESC%
echo Target: build\%BUILD_NAME%
echo.

REM Check Python
"C:\Program Files\Python312\python.exe" --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found!
    pause
    exit /b 1
)

REM Install PyInstaller if needed
"C:\Program Files\Python312\python.exe" -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing PyInstaller...
    "C:\Program Files\Python312\python.exe" -m pip install pyinstaller
)

REM Create build directory
if not exist "build" mkdir build

REM Clean previous builds
echo Cleaning previous builds...
if exist "build\%BUILD_NAME%.exe" del "build\%BUILD_NAME%.exe"
if exist "build\%BUILD_NAME%" rmdir /s /q "build\%BUILD_NAME%"

echo.
echo Compiling... Please wait...
echo.

REM Check for icon file
set ICON_PARAM=
if exist "icon.ico" (
    echo Using custom icon: icon.ico
    set ICON_PARAM=--icon=icon.ico
) else (
    echo No custom icon found, using default
)

REM Run PyInstaller
"C:\Program Files\Python312\python.exe" -m PyInstaller ^
    --name %BUILD_NAME% ^
    %BUILD_TYPE% ^
    --distpath build ^
    --workpath build\temp ^
    --specpath build ^
    %ICON_PARAM% ^
    --hidden-import PIL.Image ^
    --hidden-import numpy ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtCore ^
    --clean ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo Compilation FAILED!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Compilation SUCCESSFUL!
echo ==========================================
echo.
echo Built: %BUILD_DESC%
echo Location: build\%BUILD_NAME%
echo.

REM Show file info
if "%choice%"=="2" (
    echo Directory contents:
    dir /b "build\%BUILD_NAME%"
) else (
    if exist "build\%BUILD_NAME%.exe" (
        echo EXE file size:
        for %%A in ("build\%BUILD_NAME%.exe") do echo   %%~zA bytes
    )
)

echo.
echo Clean up temporary files? (y/n)
set /p cleanup="Choice: "
if /i "%cleanup%"=="y" (
    if exist "build\temp" rmdir /s /q "build\temp"
    echo Temporary files cleaned.
)

echo.
pause