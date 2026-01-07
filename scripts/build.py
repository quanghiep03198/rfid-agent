import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def get_git_info():
    """Get git commit info if available"""
    try:
        commit_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )

        commit_date = (
            subprocess.check_output(
                ["git", "log", "-1", "--format=%ci"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )

        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )

        return {
            "commit_hash": commit_hash,
            "commit_date": commit_date,
            "branch": branch,
        }
    except:
        return {"commit_hash": "unknown", "commit_date": "unknown", "branch": "unknown"}


def update_installer_version(version):
    """Update installer.iss file with new version"""
    installer_file = Path("installer.iss")

    if not installer_file.exists():
        print(f"Installer file not found: {installer_file}")
        return False

    try:
        # Read current content
        with open(installer_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Find and replace the version line
        import re

        version_pattern = r'(#define MyAppVersion\s+")[^"]*(")'

        # Remove 'v' prefix if present for installer
        clean_version = version[1:] if version.startswith("v") else version

        new_content = re.sub(version_pattern, f"\\g<1>{clean_version}\\g<2>", content)

        # Check if replacement was made
        if new_content == content:
            print(f"Version pattern not found in {installer_file}")
            return False

        # Write updated content
        with open(installer_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"Updated installer version to: {clean_version}")
        return True

    except Exception as e:
        print(f"Failed to update installer version: {e}")
        return False


def create_version_info(version, build_type="development"):
    """Create version info JSON file"""
    git_info = get_git_info()

    version_info = {
        "version": version,
        "build_type": build_type,
        "build_date": datetime.now().isoformat(),
        "build_timestamp": int(datetime.now().timestamp()),
        "git": git_info,
        "platform": {"system": os.name, "python_version": sys.version},
    }

    # Write to version.json
    version_file = Path("version.json")
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)

    print(f"Created version info: {version_file}")
    print(f"Version: {version}")
    print(f"Build Type: {build_type}")
    print(f"Commit: {git_info['commit_hash']}")

    return version_file


def create_windows_version_info(version):
    """Create Windows version info file for PyInstaller"""
    try:
        # Parse version to tuple (e.g., "v1.2.3-beta" -> (1,2,3,0))
        # Strip 'v' prefix and suffix like -beta, -alpha for Windows version info
        version_without_v = version[1:] if version.startswith("v") else version
        base_version = version_without_v.split("-")[0]
        version_parts = base_version.split(".")
        version_tuple = tuple(int(part) for part in version_parts) + (0,) * (
            4 - len(version_parts)
        )

        version_info_content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'GreenLand'),
        StringStruct(u'FileDescription', u'rfid-agent'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'rfid-agent'),
        StringStruct(u'LegalCopyright', u'Copyright © 2024'),
        StringStruct(u'OriginalFilename', u'rfid-agent.exe'),
        StringStruct(u'ProductName', u'rfid-agent'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""

        with open("version_info.txt", "w", encoding="utf-8") as f:
            f.write(version_info_content)

        print(f"Created Windows version info: version_info.txt")
        return Path("version_info.txt")

    except Exception as e:
        print(f"Failed to create Windows version info: {e}")
        return None


def clean_build_dirs():
    """Clean build and dist directories"""
    import shutil
    import time

    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name} directory...")

            # Try multiple times with delay for file locks
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    shutil.rmtree(dir_name)
                    break
                except PermissionError as e:
                    if attempt < max_attempts - 1:
                        print(
                            f"    Directory in use, waiting... (attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(2)
                    else:
                        print(f" Could not clean {dir_name}: {e}")
                        print(f" Please close the application and try again")
                        # Don't fail the build, just warn
                        break


def build_update_scripts():
    """Build update scripts as standalone executables"""
    try:
        # Find PyInstaller executable
        pyinstaller_cmd = find_pyinstaller()

        if not pyinstaller_cmd:
            print("PyInstaller not found!")
            print("Try installing PyInstaller: pip install pyinstaller")
            return False

        # Check if source files exist
        if not Path("update/update_manager.py").exists():
            print("update/update_manager.py not found")
            return False

        print("Building update scripts...")

        # Use the same output directory as main app
        output_dir = Path("dist") / "rfid-agent"

        # Build update_manager.py - put directly in main app directory
        update_cmd = pyinstaller_cmd + [
            str(Path("update/update_manager.py").absolute()),
            "--onefile",
            "--console",
            "--name=updater",
            f"--distpath={output_dir}",
            "--workpath=build_update",
            "--specpath=build_update",
            "--noconfirm",
            # Ensure networking/process deps are bundled in the updater build
            "--hidden-import=requests",
            "--hidden-import=urllib3",
            "--hidden-import=certifi",
            "--hidden-import=charset_normalizer",
            "--hidden-import=idna",
            "--hidden-import=psutil",
        ]

        print("Building updater.exe...")
        try:
            result = subprocess.run(
                update_cmd, check=True, capture_output=True, text=True, cwd=Path.cwd()
            )
            print(f"Output: {result.stdout[-100:] if result.stdout else 'No output'}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr}")
            raise

        # Copy additional files to the output directory
        additional_files = ["update.bat", "data_preserve.txt"]

        for file_name in additional_files:
            if Path(file_name).exists():
                import shutil

                shutil.copy2(file_name, output_dir)
                print(f"Copied: {file_name}")

        print("Update scripts built successfully!")
        print(f"Location: {output_dir}")
        print(f"Contents:")
        for item in sorted(output_dir.iterdir()):
            if item.is_file():
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"   {item.name} ({size_mb:.1f} MB)")
            else:
                print(f"   {item.name}/")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Failed to build update scripts:")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error building update scripts: {e}")
        import traceback

        traceback.print_exc()
        return False


def find_pyinstaller():
    """Find PyInstaller executable in various locations"""

    # 1. First try using module directly (most reliable)
    try:
        # Check if PyInstaller module is available
        result = subprocess.run(
            [sys.executable, "-c", "import PyInstaller"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("Using PyInstaller module")
            return [sys.executable, "-m", "PyInstaller"]
    except:
        pass

    # 2. Try executable locations
    locations = []

    # Virtual environment Scripts directory
    venv_path = Path(sys.executable).parent
    locations.append(venv_path / "pyinstaller.exe")
    locations.append(venv_path / "Scripts" / "pyinstaller.exe")

    # System Python Scripts directory
    python_path = Path(sys.executable).parent.parent
    locations.append(python_path / "Scripts" / "pyinstaller.exe")

    # Check each location
    for location in locations:
        if location.exists():
            print(f"Using PyInstaller executable at: {location}")
            return [str(location)]

    return None


def run_pyinstaller(version, include_version_file=True):
    """Run PyInstaller with the specified configuration"""

    # Find PyInstaller executable
    pyinstaller_cmd = find_pyinstaller()

    if not pyinstaller_cmd:
        print("PyInstaller not found!")
        print("Try installing PyInstaller: pip install pyinstaller")
        return False

    print(f"Using PyInstaller: {' '.join(pyinstaller_cmd)}")

    # Check PyInstaller version to determine available options
    try:
        result = subprocess.run(
            pyinstaller_cmd + ["--version"], capture_output=True, text=True
        )
        pyinstaller_version = (
            result.stdout.strip() if result.returncode == 0 else "unknown"
        )
        print(f"PyInstaller version: {pyinstaller_version}")
    except:
        pyinstaller_version = "unknown"

    cmd = pyinstaller_cmd + [
        "main.py",
        "--onedir",
        "--contents-directory=.",
        "--name=rfid-agent",
        "--distpath=dist",
        # Fix urllib3.packages.six.moves issue
        "--exclude-module=urllib3.packages.six.moves",
        "--exclude-module=six.moves",
        "--hidden-import=requests",
        "--hidden-import=urllib3",
        "--hidden-import=certifi",
        # "--hidden-import=six_moves_patch",
        # Use custom hooks for better compatibility
        "--additional-hooks-dir=pyinstaller_hooks",
    ]

    # Add optional data files if they exist
    optional_data_files = [
        ("update.bat", "."),
        ("data_preserve.txt", "."),
        # ("six_moves_patch.py", "."),
    ]

    for file_path, dest in optional_data_files:
        if os.path.exists(file_path):
            cmd.append(f"--add-data={file_path};{dest}")
            print(f"Adding data file: {file_path}")
        else:
            print(f"Skipping missing file: {file_path}")

    # Add version.json if created
    if include_version_file and os.path.exists("version.json"):
        cmd.append("--add-data=version.json;.")

    # Add Windows version info if available
    if os.path.exists("version_info.txt"):
        cmd.append("--version-file=version_info.txt")

    print(f"Building with PyInstaller...")
    print(
        f"Command: {' '.join(cmd[:3])}...{' '.join(cmd[-3:])}"
    )  # Show abbreviated command

    try:
        # Run without capturing output to see real-time progress
        print("Running PyInstaller (this may take a few minutes)...")
        result = subprocess.run(cmd, check=True, cwd=Path.cwd())
        print("Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code: {e.returncode}")
        print(f"Command: {' '.join(cmd)}")
        return False
    except FileNotFoundError as e:
        print(f"PyInstaller executable not found: {e}")
        print("Make sure PyInstaller is installed: pip install pyinstaller")
        return False
    except KeyboardInterrupt:
        print(f"Build interrupted by user")
        return False
    except Exception as e:
        print(f"Unexpected error during build: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Build rfid-agent")
    parser.add_argument(
        "--version",
        required=True,
        help="Version number with v prefix (e.g., v1.2.3, v1.2.3-beta)",
    )
    parser.add_argument(
        "--type",
        choices=["development", "release", "beta"],
        default="development",
        help="Build type (default: development)",
    )
    parser.add_argument(
        "--no-version-file", action="store_true", help="Skip creating version.json file"
    )
    parser.add_argument(
        "--no-clean", action="store_true", help="Skip cleaning build directories"
    )

    args = parser.parse_args()

    print(f"Building rfid-agent {args.version}")
    print(f"Build Type: {args.type}")
    print(f"Working Directory: {os.getcwd()}")

    # Validate version format (must start with 'v' and allow suffixes like -beta, -alpha, etc.)
    if not args.version.startswith("v"):
        print("Version must start with 'v' (e.g., v1.2.3, v1.2.3-beta)")
        sys.exit(1)

    try:
        # Remove 'v' prefix and split on first hyphen to separate base version from suffix
        version_without_v = args.version[1:]  # Remove 'v' prefix
        base_version = version_without_v.split("-")[0]
        version_parts = base_version.split(".")
        if len(version_parts) < 2 or len(version_parts) > 4:
            raise ValueError("Invalid version format")
        for part in version_parts:
            int(part)  # Ensure each part is a number
    except ValueError:
        print(
            " Invalid version format. Use semantic versioning with 'v' prefix (e.g., v1.2.3, v1.2.3-beta)"
        )
        sys.exit(1)

    # Clean build directories
    if not args.no_clean:
        clean_build_dirs()

    # Update installer version (always update regardless of version file option)
    update_installer_version(args.version)

    # Create version info
    include_version_file = not args.no_version_file
    if include_version_file:
        create_version_info(args.version, args.type)
        create_windows_version_info(args.version)

    # Run PyInstaller first to create main app
    success = run_pyinstaller(args.version, include_version_file)

    if success:
        # Build update scripts into the same directory as main app
        if not build_update_scripts():
            print("Failed to build update scripts, but main app built successfully")
            print("Update functionality may not work without Python installed")
        else:
            print("Update scripts built into app directory")

    if success:
        print(f"\nBuild completed successfully!")
        print(f"Output directory: {os.path.abspath('dist')}")

        # Show build artifacts
        dist_path = Path("dist/rfid-agent")
        if dist_path.exists():
            exe_path = dist_path / "rfid-agent.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"Executable: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
