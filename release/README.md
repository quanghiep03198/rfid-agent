# Installation Assets

This folder contains pre-built installation packages that will be included in GitHub releases.

## Current Files

- `rfid-agent-1.0.1-install-windows-x64.exe` - Windows installer (executable)
- `rfid-agent-1.0.1-windows-x64-version.rar` - Portable version (legacy, for reference)

## How it works

When you create a release using the GitHub Actions workflow:

1. **Files are automatically copied** from this folder to the release assets
2. **Fresh portable ZIP is created** from the latest build automatically
3. **Professional installers** (if available) are included from this folder

## What gets created automatically:

✅ **Fresh Portable ZIP**: `rfid-agent-v{version}-windows-x64.zip` (created from latest build)  
✅ **Installation Files**: All files from this folder are included as-is  
✅ **Professional Release**: Multiple download options for users

## Updating Installation Files

### Option 1: Automatic (Recommended)

Just create a release - the workflow automatically:

- Builds the latest code using `py scripts/build.py --version <version_value> --type <release|development|test>`
- Creates a fresh portable ZIP archive
- Includes all files from this folder

### Option 2: Update Pre-built Installers

1. Replace installer files in this folder with new versions
2. Keep existing filenames (no renaming needed)
3. Create a release - everything gets included automatically

## Current Workflow Benefits

🚀 **Simplified Process**: Windows-only builds for faster CI/CD  
📦 **Automatic Packaging**: Creates portable ZIP from fresh builds  
🔧 **Professional Installers**: Includes your custom installers  
⚡ **Efficient**: No manual ZIP creation needed

## File Types Supported

- `.exe` - Windows executables/installers
- `.msi` - Windows MSI packages
- `.zip` - Compressed archives (auto-generated)
- `.rar` - WinRAR archives (legacy)

## Creating New Installation Packages

### Windows Installer (Inno Setup/NSIS)

1. Use your preferred installer tool (Inno Setup, NSIS, etc.)
2. Create installer targeting the `dist/rfid-agent/` folder structure
3. Place the resulting installer in this folder
4. It will be included in the next release automatically

### Portable Package (Automatic)

- The release workflow automatically creates `rfid-agent-v{version}-windows-x64.zip`
- Contains the complete "rfid-agent" folder with all dependencies
- No manual creation needed

### Advanced Packaging

For professional installers:

1. Create installer using Inno Setup, NSIS, or Advanced Installer
2. Target the directory structure from `dist/rfid-agent/`
3. Place finished installer in this folder
4. Release workflow includes it automatically

## Testing Your Installers

Before releasing, test your installation packages:

1. **Clean system test**: Install on a system without Python/dependencies
2. **Functionality test**: Verify the application runs correctly
3. **Uninstall test**: Test the uninstall process works properly
4. **Shortcuts test**: Check desktop/start menu shortcuts work

## Example Release Assets

A typical release will include:

```
Release v1.2.3 Assets:
├── rfid-agent-1.0.1-install-windows-x64.exe # Your custom installer
├── rfid-agent-1.0.1-windows-x64.rar           # Legacy portable (reference)
└── [other files from this folder]          # Additional installers
```

## Workflow Integration

The GitHub Actions workflow:

1. ✅ Builds fresh executable using `scripts/build.bat`
2. ✅ Creates portable ZIP from the build output
3. ✅ Copies all files from this installation folder
4. ✅ Creates professional release with multiple download options
