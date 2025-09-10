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

1. Go to **Actions** tab in GitHub
2. Click **Create Release** workflow
3. Click **Run workflow**
4. Enter the version number (e.g., `1.2.3`)
5. Optionally mark as pre-release
6. Click **Run workflow**

### Version Format

Use semantic versioning:

- `1.0.0` - Major release
- `1.1.0` - Minor release
- `1.1.1` - Patch release
- `1.1.1-beta` - Pre-release

### What happens:

1. ✅ Validates version format
2. ✅ Checks if tag already exists
3. ✅ Builds executables with version in filename
4. ✅ Generates changelog from commits
5. ✅ Creates GitHub release with assets
6. ✅ Makes it the latest release (unless pre-release)

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
