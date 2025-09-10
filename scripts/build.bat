
@echo off
REM RFID Agent Build Script for Windows
REM This script builds the RFID Agent application using PyInstaller
REM
REM Author: RFID Agent Team
REM Version: 2.0
REM Last Updated: September 2025

setlocal enabledelayedexpansion

echo.
echo ================================================
echo  RFID Agent Build Script for Windows
echo ================================================
echo.

REM Check if Python is available
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo [ERROR] Please install Python and ensure it's in your PATH
    echo [ERROR] Download from: https://python.org/downloads/
    pause
    exit /b 1
)

REM Get Python version for logging
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [INFO] Using Python %PYTHON_VERSION%

REM Check if PyInstaller is installed
echo [INFO] Checking PyInstaller installation...
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller is not installed
    echo [ERROR] Please install it with: python -m pip install pyinstaller
    pause
    exit /b 1
)

REM Get PyInstaller version for logging
for /f "tokens=*" %%i in ('python -m PyInstaller --version 2^>^&1') do set PYINSTALLER_VERSION=%%i
echo [INFO] Using PyInstaller %PYINSTALLER_VERSION%

REM Check if main.py exists
echo [INFO] Checking project files...
if not exist "main.py" (
    echo [ERROR] main.py not found in current directory
    echo [ERROR] Please run this script from the project root directory
    pause
    exit /b 1
)

REM Check if icon.ico exists
if not exist "icon.ico" (
    echo [WARNING] icon.ico not found - build will continue without icon
    set ICON_PARAM=
) else (
    echo [INFO] Found icon.ico
    set ICON_PARAM=--icon=icon.ico
)

echo.
echo [INFO] Starting build process...
echo [INFO] Cleaning previous builds...

REM Clean previous builds with error handling
if exist "dist" (
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo [WARNING] Could not completely remove dist directory
        echo [WARNING] Some files may be in use
    ) else (
        echo [INFO] Removed dist directory
    )
)

if exist "build" (
    rmdir /s /q "build" 2>nul
    if exist "build" (
        echo [WARNING] Could not completely remove build directory
        echo [WARNING] Some files may be in use
    ) else (
        echo [INFO] Removed build directory
    )
)

echo.
echo [INFO] Building application with PyInstaller...
echo [INFO] This may take a few minutes...

REM Build with PyInstaller
python -m PyInstaller main.py ^
    --contents-directory . ^
    --name "RFID Agent" ^
    --add-data="icon.ico;." ^
    %ICON_PARAM% ^
    --onedir ^
    --noconfirm

REM Check if build was successful
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed with exit code %errorlevel%
    echo [ERROR] Please check the error messages above
    pause
    exit /b %errorlevel%
)

REM Verify output directory exists
if not exist "dist\RFID Agent" (
    echo.
    echo [ERROR] Build completed but output directory not found
    echo [ERROR] Expected: dist\RFID Agent
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Build completed successfully!
echo [SUCCESS] Output directory: dist\RFID Agent
echo.
echo [INFO] Build contents:
dir "dist\RFID Agent" /b

REM Calculate directory size
for /f "tokens=3" %%i in ('dir "dist\RFID Agent" /s /-c ^| find "bytes"') do set BUILD_SIZE=%%i
echo.
echo [INFO] Total build size: %BUILD_SIZE% bytes

echo.
echo [INFO] You can now:
echo        - Test the application: "dist\RFID Agent\RFID Agent.exe"
echo        - Create a ZIP archive of the "dist\RFID Agent" folder
echo        - Use the folder with installer tools like Inno Setup
echo.
echo [SUCCESS] Build process completed.