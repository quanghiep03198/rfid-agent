# Release Workflow Updates Summary

## Overview

The release workflow has been updated to support creating releases for the latest tag automatically, while maintaining compatibility with manual releases.

## New Features

### 1. Automatic Tag-based Releases

- **Trigger**: When you push a tag like `v1.2.3`, the workflow automatically runs
- **Behavior**: Creates a release for that specific tag
- **Benefits**: No manual intervention needed after creating tags

### 2. Latest Tag Detection

- **Default Behavior**: Uses the latest existing tag when run manually
- **Manual Override**: Can specify a custom version if needed
- **Validation**: Ensures releases don't conflict with existing ones

### 3. Multiple Trigger Methods

#### Automatic (Recommended)

```bash
# Create and push a tag
git tag v1.2.3
git push origin v1.2.3
# Release is created automatically
```

#### Manual with Latest Tag (Default)

1. Go to Actions → Create Release → Run workflow
2. Leave version empty (uses latest tag)
3. Set prerelease if needed
4. Click Run workflow

#### Manual with Custom Version

1. Go to Actions → Create Release → Run workflow
2. Uncheck "Use latest tag"
3. Enter version (e.g., 1.2.3)
4. Set prerelease if needed
5. Click Run workflow

## Workflow Inputs

- **version**: Custom version (optional, ignored if use_latest_tag is true)
- **prerelease**: Mark as pre-release (default: false)
- **use_latest_tag**: Use latest repository tag (default: true)

## Benefits

✅ **Automatic Releases**: Push tag → Release created automatically  
✅ **Latest Tag Support**: No need to remember version numbers  
✅ **Backward Compatible**: Manual releases still work  
✅ **Smart Changelog**: Generates changes between tags automatically  
✅ **Conflict Prevention**: Checks for existing releases before creating

## Example Workflow

```bash
# 1. Make changes and commit
git add .
git commit -m "feat: new awesome feature"
git push origin main

# 2. Create and push tag
git tag v1.3.0
git push origin v1.3.0

# 3. Release is created automatically with:
#    - Build from the tagged commit
#    - Changelog with changes since previous tag
#    - Portable ZIP package
#    - Installation assets (if available)
```

## Migration Notes

- **No Breaking Changes**: Existing manual workflow continues to work
- **Default Behavior**: Now uses latest tag instead of requiring manual input
- **Tag Format**: Must follow `v*.*.*` pattern (e.g., v1.2.3, v2.0.0-beta)
- **Release Names**: Automatically generated as "Release v1.2.3"

This update makes the release process more automated while maintaining flexibility for special cases.
