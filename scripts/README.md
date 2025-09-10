# Build Scripts

This directory contains build scripts for different platforms and use cases.

## Available Scripts

### Windows Build Scripts

- **`build.bat`** - Professional Windows build script

  - Comprehensive error checking and validation
  - Python and PyInstaller dependency verification
  - Detailed logging and progress reporting
  - Build success confirmation and size calculation
  - User-friendly error messages and guidance
  - Used by GitHub Actions workflow

### Linux/macOS Build Scripts

- **`build.sh`** - Full-featured Linux/macOS build script

  - Comprehensive error checking
  - Automatic Python/Python3 detection
  - PyInstaller dependency verification
  - Build success confirmation
  - Detailed output and logging

### Test Scripts

- **`test.bat`** - Windows testing script
- **`test.sh`** - Linux/macOS testing script

## Usage

### Windows

```batch
# Build the application (recommended)
scripts\build.bat

# Run tests
scripts\test.bat
```

### Linux/macOS

```bash
# Make scripts executable (one time setup)
chmod +x scripts/build.sh
chmod +x scripts/test.sh

# Build the application (recommended)
./scripts/build.sh

# Run tests
./scripts/test.sh
```

## Output

All build scripts create the same output structure:

```
dist/
└── RFID Agent/
    ├── RFID Agent          # Executable (Linux/macOS)
    ├── RFID Agent.exe      # Executable (Windows)
    ├── icon.ico            # Application icon
    └── [dependencies]      # PyInstaller bundled files
```

## Requirements

- Python 3.10+ with PyInstaller installed
- All project dependencies installed (`pip install -r requirements.txt`)

## Platform-Specific Notes

### Linux

- May require additional system dependencies for GUI applications
- Some distributions need `python3-tk` for tkinter support

### macOS

- May require code signing for distribution
- App bundles can be created with additional PyInstaller options

### Windows

- Works with both Command Prompt and PowerShell
- Compatible with GitHub Actions Windows runners

## GitHub Actions Integration

The **CI/CD workflow** uses:

- `scripts/build.bat` on Windows runners
- Could be extended to use `scripts/build.sh` for Linux/macOS builds

The **Release workflow** currently focuses on Windows builds but can be expanded to include cross-platform builds using these scripts.
