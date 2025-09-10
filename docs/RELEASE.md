# Release Process

## Overview

This project has two GitHub Actions workflows for different purposes:

1. **CI/CD Pipeline** (`ci.yaml`) - Runs automatically on push/PR
2. **Create Release** (`release.yaml`) - Manual workflow for creating releases

## Automatic CI/CD Pipeline

The CI/CD pipeline runs automatically when you:

- Push to `main`, `develop`, or `feat/*` branches
- Create pull requests to `main` or `develop`

### What it does:

- ✅ Runs tests on Python 3.10, 3.11, and 3.12
- ✅ Performs security scans (bandit, safety)
- ✅ Builds executables for Windows, Linux, and macOS
- ✅ Generates coverage reports
- ❌ **Does NOT create releases automatically** (to avoid conflicts)

### Special Release Trigger

The CI pipeline will only create a release if:

- You're pushing to `main` branch
- Your commit message contains `release:` (e.g., "release: v1.2.3")

## Manual Release Process

For better control over releases, use the manual "Create Release" workflow:

### Steps:

1. **Build installation packages locally** (optional):

   ```bash
   # Windows (builds directory structure + creates ZIP)
   scripts\build-release.bat 1.2.3

   # Or just use the simple build script
   scripts\build.bat
   ```

2. Go to **Actions** tab in GitHub
3. Click **Create Release** workflow
4. Click **Run workflow**
5. Enter the version number (e.g., `1.2.3`)
6. Optionally mark as pre-release
7. Click **Run workflow**

### What gets included automatically:

- ✅ **Windows Executable**: Built from source using PyInstaller (directory structure)
- ✅ **Portable ZIP Archive**: Complete "RFID Agent" folder packaged for easy download
- ✅ **Installation files**: Any files in the `installation/` folder
- ✅ **Professional installer**: Pre-built installers (if available)

The workflow automatically:

- Builds the application using your `build.bat` script (Windows only)
- Creates a portable ZIP archive of the complete application folder
- Includes any pre-built installers from the installation folder
- Generates a detailed changelog with download options

### Version Format

Use semantic versioning:

- `1.0.0` - Major release
- `1.1.0` - Minor release
- `1.1.1` - Patch release
- `1.1.1-beta` - Pre-release

### What happens:

1. ✅ Validates version format
2. ✅ Checks if tag already exists
3. ✅ Builds Windows executable using `scripts/build.bat`
4. ✅ Creates portable ZIP archive of the "RFID Agent" folder
5. ✅ Copies files from `installation/` folder as release assets
6. ✅ Generates changelog from commits
7. ✅ Creates GitHub release with all assets
8. ✅ Makes it the latest release (unless pre-release)

## Installation Folder Structure

Place your installation files in the `installation/` folder to include them in releases:

```
installation/
├── rfid-agent-1.0.0-install-windows-x64.exe  # Windows installer
├── rfid-agent-1.0.0-portable.rar             # Portable version (legacy)
├── README.md                                  # Installation documentation
└── [other installer files]                   # Additional installers
```

**Note**: The workflow creates a fresh portable ZIP from the built application,
so you don't need to manually update portable packages.

- `rfid-agent-installer.exe` → `rfid-agent-v1.2.3-installer.exe`
- `rfid-agent-portable.zip` → `rfid-agent-v1.2.3-portable.zip`

## Build Scripts

Use the build scripts to create installation packages across different platforms:

### Windows (`scripts/build.bat`)

```bash
scripts\build.bat
```

Creates:

- Complete application folder in `dist/RFID Agent/`
- All dependencies included
- Ready for ZIP packaging or installer creation

### Linux/macOS (`scripts/build.sh`)

```bash
# Make executable (one time)
chmod +x scripts/build.sh

# Run build
./scripts/build.sh
```

Features:

- Full error checking and validation
- Automatic Python/Python3 detection
- PyInstaller dependency verification
- Build success confirmation

### Simple Linux/macOS (`scripts/build-simple.sh`)

```bash
chmod +x scripts/build-simple.sh
./scripts/build-simple.sh
```

- Minimal version without error checking
- Quick builds for development

### Enhanced Windows Build (`scripts/build-release.bat`)

```bash
scripts\build-release.bat 1.2.3
```

Creates:

- Executable with PyInstaller
- Portable ZIP package
- Windows installer (if NSIS is installed)

**Note**: The GitHub Actions workflow uses the simple `build.bat` and creates
the portable ZIP automatically, so manual ZIP creation is usually not needed.

## Current Workflow Focus

The project now focuses on **Windows-only builds** for efficiency:

- ✅ **Faster CI/CD**: Only builds on Windows instead of 3 platforms
- ✅ **Uses your build script**: Leverages tested `scripts/build.bat`
- ✅ **Directory structure**: Works well with installer tools like Inno Setup
- ✅ **Automatic portable package**: Creates ZIP archive automatically

## Troubleshooting

### "Tag already exists" error

- Check existing releases: https://github.com/your-repo/releases
- Use a different version number
- Delete the existing tag if needed: `git tag -d v1.0.0 && git push origin :refs/tags/v1.0.0`

### "Not Found" error in release creation

- Usually caused by trying to update an existing release
- The new workflow prevents this by checking for existing tags first

### Assets not uploading

- Check that the build step completed successfully
- Verify artifact names match the `files:` pattern in the workflow

## Best Practices

1. **Use semantic versioning** (MAJOR.MINOR.PATCH)
2. **Test thoroughly** before creating releases
3. **Use descriptive commit messages** for better changelogs
4. **Create pre-releases** for beta versions
5. **Manually verify** releases after creation

## Example Workflow

```bash
# 1. Make your changes
git add .
git commit -m "feat: add new RFID scanning feature"
git push origin main

# 2. Wait for CI to pass (check Actions tab)

# 3. Create release manually:
#    - Go to Actions → Create Release → Run workflow
#    - Enter version: 1.1.0
#    - Click Run workflow

# 4. Release is created with:
#    - Tag: v1.1.0
#    - Binaries for all platforms
#    - Auto-generated changelog
```
