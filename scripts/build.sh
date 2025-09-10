#!/bin/bash

# RFID Agent Build Script for Linux/macOS
# This script builds the RFID Agent application using PyInstaller

set -e  # Exit on any error

echo "Starting RFID Agent build process..."

# Check if Python is available
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo "Error: Python is not installed or not in PATH"
        exit 1
    fi
else
    PYTHON_CMD="python"
fi

echo "Using Python command: $PYTHON_CMD"

# Check if PyInstaller is installed
if ! $PYTHON_CMD -m PyInstaller --version &> /dev/null; then
    echo "Error: PyInstaller is not installed"
    echo "Please install it with: $PYTHON_CMD -m pip install pyinstaller"
    exit 1
fi

echo "Cleaning previous builds..."
rm -rf dist
rm -rf build

echo "Building application with PyInstaller..."
$PYTHON_CMD -m PyInstaller main.py \
    --contents-directory . \
    --name "RFID Agent" \
    --add-data="icon.ico:." \
    --icon=icon.ico \
    --onedir

# Check if build was successful
if [ -d "dist/RFID Agent" ]; then
    echo "✅ Build completed successfully!"
    echo "📁 Output directory: dist/RFID Agent"
    echo "📊 Build contents:"
    ls -la "dist/RFID Agent"
else
    echo "❌ Build failed - output directory not found"
    exit 1
fi
