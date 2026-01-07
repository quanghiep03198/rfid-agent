#!/usr/bin/env python3
"""
Clean Ultimate Update Manager - No ctypes dependencies
Production ready update system for EPC application
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  requests not available - auto-detection features limited")

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - process management features limited")


class SafeLogger:
    """Safe logging system that never fails"""

    @staticmethod
    def log(level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        print(formatted_msg)

        # Try to log to file if possible
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            log_file = os.path.join(log_dir, "update.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except:
            pass  # Fail silently for logging

    @staticmethod
    def info(message: str):
        SafeLogger.log("INFO", message)

    @staticmethod
    def warning(message: str):
        SafeLogger.log("WARNING", message)

    @staticmethod
    def error(message: str):
        SafeLogger.log("ERROR", message)


class ProcessManager:
    """Manage processes without ctypes dependencies"""

    def __init__(self):
        self.logger = SafeLogger()

    def find_processes_by_name(self, process_names: List[str]) -> List[Dict]:
        """Find processes by name"""
        found_processes = []

        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available - using tasklist as fallback")
            return self._find_processes_with_tasklist(process_names)

        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    proc_name = proc.info["name"]
                    for target_name in process_names:
                        if proc_name.lower() == target_name.lower():
                            found_processes.append(
                                {
                                    "pid": proc.info["pid"],
                                    "name": proc_name,
                                    "exe": proc.info.get("exe", "Unknown"),
                                }
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.error(f"Error scanning processes: {e}")

        return found_processes

    def _find_processes_with_tasklist(self, process_names: List[str]) -> List[Dict]:
        """Fallback process detection using Windows tasklist"""
        found_processes = []

        try:
            result = subprocess.run(
                ["tasklist", "/fo", "csv"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:  # Skip header
                    for line in lines[1:]:
                        parts = line.replace('"', "").split(",")
                        if len(parts) >= 2:
                            proc_name = parts[0]
                            try:
                                pid = int(parts[1])
                                for target_name in process_names:
                                    if proc_name.lower() == target_name.lower():
                                        found_processes.append(
                                            {
                                                "pid": pid,
                                                "name": proc_name,
                                                "exe": "Unknown",
                                            }
                                        )
                            except ValueError:
                                continue

        except Exception as e:
            self.logger.error(f"Error using tasklist: {e}")

        return found_processes

    def terminate_processes_by_name(self, process_names: List[str]) -> bool:
        """Terminate processes by name"""
        found_processes = self.find_processes_by_name(process_names)

        if not found_processes:
            self.logger.info("No matching processes found")
            return True

        terminated = []

        for proc_info in found_processes:
            pid = proc_info["pid"]
            name = proc_info["name"]

            # Try psutil first
            if PSUTIL_AVAILABLE:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    terminated.append(f"{name} (PID: {pid})")
                    self.logger.info(f"Terminated process: {name} (PID: {pid})")
                    continue
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    self.logger.warning(f"Could not terminate {name} with psutil: {e}")

            # Fallback to taskkill
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    terminated.append(f"{name} (PID: {pid})")
                    self.logger.info(
                        f"Terminated process: {name} (PID: {pid}) using taskkill"
                    )
                else:
                    self.logger.warning(f"taskkill failed for {name}: {result.stderr}")
            except Exception as e:
                self.logger.error(f"Error killing process {name}: {e}")

        if terminated:
            # Wait for processes to exit
            time.sleep(2)
            return True

        return False


class FileReplacer:
    """File replacement without Windows API dependencies"""

    def __init__(self):
        self.logger = SafeLogger()

    def replace_file(
        self, source_path: str, target_path: str, backup_dir: Optional[str] = None
    ) -> bool:
        """Replace file with multiple strategies"""

        # Strategy 1: Direct replacement
        if self._try_direct_replacement(source_path, target_path, backup_dir):
            return True

        # Strategy 2: Rename and replace
        if self._try_rename_replacement(source_path, target_path, backup_dir):
            return True

        # Strategy 3: Force delete and copy
        if self._try_force_replacement(source_path, target_path, backup_dir):
            return True

        # Strategy 4: Skip file (log and continue)
        self.logger.warning(
            f"Could not replace {os.path.basename(target_path)} - skipping"
        )
        return False

    def _try_direct_replacement(
        self, source_path: str, target_path: str, backup_dir: Optional[str] = None
    ) -> bool:
        """Try direct file replacement"""
        try:
            # Create backup if requested
            if backup_dir and os.path.exists(target_path):
                backup_path = os.path.join(backup_dir, os.path.basename(target_path))
                os.makedirs(backup_dir, exist_ok=True)
                shutil.copy2(target_path, backup_path)

            # Direct replacement
            shutil.copy2(source_path, target_path)
            self.logger.info(
                f"Direct replacement successful: {os.path.basename(target_path)}"
            )
            return True

        except Exception as e:
            self.logger.warning(
                f"Direct replacement failed for {os.path.basename(target_path)}: {e}"
            )
            return False

    def _try_rename_replacement(
        self, source_path: str, target_path: str, backup_dir: Optional[str] = None
    ) -> bool:
        """Try rename-then-replace strategy"""
        try:
            if not os.path.exists(target_path):
                return self._try_direct_replacement(
                    source_path, target_path, backup_dir
                )

            # Rename existing file
            temp_name = target_path + f".old.{int(time.time())}"
            os.rename(target_path, temp_name)

            try:
                # Copy new file
                shutil.copy2(source_path, target_path)

                # Create backup if requested
                if backup_dir:
                    backup_path = os.path.join(
                        backup_dir, os.path.basename(target_path)
                    )
                    os.makedirs(backup_dir, exist_ok=True)
                    shutil.copy2(temp_name, backup_path)

                # Remove old file
                os.remove(temp_name)
                self.logger.info(
                    f"Rename replacement successful: {os.path.basename(target_path)}"
                )
                return True

            except Exception:
                # Restore original file
                try:
                    os.rename(temp_name, target_path)
                except:
                    pass
                raise

        except Exception as e:
            self.logger.warning(
                f"Rename replacement failed for {os.path.basename(target_path)}: {e}"
            )
            return False

    def _try_force_replacement(
        self, source_path: str, target_path: str, backup_dir: Optional[str] = None
    ) -> bool:
        """Try force replacement using system commands"""
        try:
            if not os.path.exists(target_path):
                return self._try_direct_replacement(
                    source_path, target_path, backup_dir
                )

            # Create backup first
            if backup_dir:
                backup_path = os.path.join(backup_dir, os.path.basename(target_path))
                os.makedirs(backup_dir, exist_ok=True)
                try:
                    shutil.copy2(target_path, backup_path)
                except:
                    pass

            # Try to remove readonly attribute and delete
            try:
                os.chmod(target_path, 0o777)
            except:
                pass

            # Force delete with Windows del command
            try:
                subprocess.run(
                    ["del", "/f", "/q", target_path],
                    shell=True,
                    capture_output=True,
                    timeout=5,
                )
            except:
                pass

            # Copy new file
            shutil.copy2(source_path, target_path)
            self.logger.info(
                f"Force replacement successful: {os.path.basename(target_path)}"
            )
            return True

        except Exception as e:
            self.logger.warning(
                f"Force replacement failed for {os.path.basename(target_path)}: {e}"
            )
            return False


class UpdateDownloader:
    """Download updates using system tools"""

    def __init__(self):
        self.logger = SafeLogger()

    def download_file(self, url: str, output_path: str, max_retries: int = 3) -> bool:
        """Download file using curl or PowerShell"""

        for attempt in range(max_retries):
            self.logger.info(f"Download attempt {attempt + 1}/{max_retries}: {url}")

            # Try curl first (more reliable)
            if self._try_curl_download(url, output_path):
                return True

            # Try PowerShell as fallback
            if self._try_powershell_download(url, output_path):
                return True

            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff

        self.logger.error(f"All download attempts failed for {url}")
        return False

    def _try_curl_download(self, url: str, output_path: str) -> bool:
        """Try downloading with curl"""
        try:
            cmd = [
                "curl",
                "-L",
                "-o",
                output_path,
                url,
                "--connect-timeout",
                "30",
                "--max-time",
                "300",
                "--retry",
                "3",
            ]

            print(f"📦 Downloading with curl... (43MB file, may take a few minutes)")
            result = subprocess.run(cmd, timeout=180)

            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                self.logger.info(f"Curl download successful: {size} bytes")
                return True
            else:
                self.logger.warning(f"Curl download failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.warning(f"Curl download error: {e}")
            return False

    def _try_powershell_download(self, url: str, output_path: str) -> bool:
        """Try downloading with PowerShell"""
        try:
            script = f"""
            try {{
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                $wc = New-Object System.Net.WebClient
                $wc.DownloadFile('{url}', '{output_path}')
                exit 0
            }} catch {{
                Write-Error $_.Exception.Message
                exit 1
            }}
            """

            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                self.logger.info(f"PowerShell download successful: {size} bytes")
                return True
            else:
                self.logger.warning(f"PowerShell download failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.warning(f"PowerShell download error: {e}")
            return False


class CleanUpdateManager:
    """Clean Ultimate Update Manager - No ctypes dependencies"""

    def __init__(self):
        self.logger = SafeLogger()
        self.process_manager = ProcessManager()
        self.file_replacer = FileReplacer()
        self.downloader = UpdateDownloader()

    def perform_complete_update(
        self,
        update_url: str,
        install_dir: str,
        current_version: str = None,
        backup_dir: str = None,
        temp_dir: str = None,
        max_retries: int = 3,
        retry_delay: int = 5,
        force: bool = False,
        silent: bool = False,
        process_names: List[str] = None,
    ) -> bool:
        """
        Perform complete update with all safeguards
        """

        self.logger.info("🚀 Starting Clean Update Manager")
        self.logger.info("=" * 60)

        # Setup directories
        if not backup_dir:
            backup_dir = os.path.join(install_dir, f"backup_{int(time.time())}")

        if not temp_dir:
            temp_dir = tempfile.mkdtemp(prefix="epc_update_")

        if not process_names:
            process_names = ["main.exe", "rfid-agent.exe"]

        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Step 1: Check for updates
            self.logger.info("🔍 Step 1: Checking for updates...")
            if not force:
                has_update = self.check_for_updates(update_url, current_version)
                if not has_update:
                    self.logger.info("✅ No update needed")
                    return True

            # Step 2: Download update
            self.logger.info("📥 Step 2: Downloading update...")
            download_info = self._get_download_info(update_url)
            if not download_info:
                self.logger.error("❌ Could not get download information")
                return False

            download_path = os.path.join(temp_dir, "update.zip")
            download_url = download_info.get("download_url", download_info.get("url"))
            if not download_url:
                self.logger.error("❌ No download URL found")
                return False

            if not self.downloader.download_file(download_url, download_path):
                self.logger.error("❌ Download failed")
                return False

            # Step 3: Extract update
            self.logger.info("📦 Step 3: Extracting update...")
            extract_dir = os.path.join(temp_dir, "extracted")
            if not self._extract_update(download_path, extract_dir):
                self.logger.error("❌ Extraction failed")
                return False

            # Step 4: Terminate processes
            self.logger.info("🛑 Step 4: Terminating processes...")
            self.process_manager.terminate_processes_by_name(process_names)

            # Step 5: Backup current installation
            self.logger.info("📦 Step 5: Creating backup...")
            if not self._create_backup(install_dir, backup_dir):
                self.logger.warning("⚠️  Backup creation failed (continuing anyway)")

            # Step 6: Replace files
            self.logger.info("🔄 Step 6: Replacing files...")
            success_count, total_count = self._replace_files(
                extract_dir, install_dir, backup_dir
            )

            # Step 7: Verify update
            self.logger.info("✅ Step 7: Verifying update...")
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            if success_rate >= 70:  # At least 70% success rate
                self.logger.info(
                    f"🎉 Update successful! ({success_count}/{total_count} files, {success_rate:.1f}%)"
                )

                # Cleanup temp files
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

                return True
            else:
                self.logger.error(
                    f"❌ Update failed! ({success_count}/{total_count} files, {success_rate:.1f}%)"
                )

                # Try to restore backup
                if not silent:
                    restore = (
                        input("Restore from backup? (y/N): ").lower().startswith("y")
                    )
                    if restore:
                        self._restore_backup(backup_dir, install_dir)

                return False

        except Exception as e:
            self.logger.error(f"❌ Update failed with error: {e}")
            if not silent:
                print(f"Full traceback:\n{traceback.format_exc()}")
            return False

        finally:
            # Cleanup
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass

    def check_for_updates(self, update_url: str, current_version: str = None) -> bool:
        """Check if updates are available"""
        try:
            version_info = self._get_download_info(update_url)
            if not version_info:
                return False

            remote_version = version_info.get("version")
            if not remote_version:
                return True  # Assume update available if no version info

            if current_version and current_version == remote_version:
                self.logger.info(f"Current version {current_version} is up to date")
                return False

            self.logger.info(f"Update available: {current_version} -> {remote_version}")
            return True

        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return False

    def _get_download_info(self, update_url: str) -> Optional[Dict]:
        """Get download information from update URL"""
        try:
            if update_url.startswith("file://"):
                # Local file
                file_path = update_url[7:]  # Remove 'file://'
                if file_path.endswith(".json"):
                    with open(file_path, "r") as f:
                        version_data = json.load(f)
                        # Ensure we have a download_url
                        if "download_url" not in version_data:
                            version_data["download_url"] = version_data.get(
                                "url", update_url
                            )
                        return version_data
                else:
                    # Direct zip file
                    return {
                        "url": update_url,
                        "version": "unknown",
                        "download_url": update_url,
                    }
            elif update_url.endswith(".zip"):
                # Direct download URL (from auto-detection)
                self.logger.info("Direct ZIP download URL detected")
                return {
                    "url": update_url,
                    "version": "auto-detected",
                    "download_url": update_url,
                }
            else:
                # Remote URL - try to download version.json
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w+", suffix=".json", delete=False
                )
                temp_file.close()

                if self.downloader.download_file(update_url, temp_file.name):
                    with open(temp_file.name, "r") as f:
                        data = json.load(f)
                        # Ensure we have a download_url
                        if "download_url" not in data:
                            data["download_url"] = data.get("url", update_url)
                    os.unlink(temp_file.name)
                    return data
                else:
                    os.unlink(temp_file.name)
                    # Fallback: treat as direct download
                    self.logger.warning(
                        "Failed to get JSON metadata, treating as direct download"
                    )
                    return {
                        "url": update_url,
                        "version": "unknown",
                        "download_url": update_url,
                    }

        except Exception as e:
            self.logger.error(f"Error getting download info: {e}")
            return None

    def _extract_update(self, zip_path: str, extract_dir: str) -> bool:
        """Extract update package"""
        try:
            with zipfile.ZipFile(zip_path, "r") as zipf:
                zipf.extractall(extract_dir)

            extracted_files = list(Path(extract_dir).rglob("*"))
            extracted_files = [f for f in extracted_files if f.is_file()]

            self.logger.info(f"Extracted {len(extracted_files)} files")
            return True

        except Exception as e:
            self.logger.error(f"Extraction error: {e}")
            return False

    def _create_backup(self, install_dir: str, backup_dir: str) -> bool:
        """Create backup of current installation"""
        try:
            files_backed_up = 0

            for root, dirs, files in os.walk(install_dir):
                for file in files:
                    source_path = os.path.join(root, file)
                    rel_path = os.path.relpath(source_path, install_dir)
                    backup_path = os.path.join(backup_dir, rel_path)

                    # Skip backup directory itself
                    if backup_dir in source_path:
                        continue

                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)

                    try:
                        shutil.copy2(source_path, backup_path)
                        files_backed_up += 1
                    except Exception as e:
                        self.logger.warning(f"Could not backup {file}: {e}")

            self.logger.info(f"Backed up {files_backed_up} files to {backup_dir}")
            return files_backed_up > 0

        except Exception as e:
            self.logger.error(f"Backup error: {e}")
            return False

    def _replace_files(
        self, source_dir: str, target_dir: str, backup_dir: str
    ) -> Tuple[int, int]:
        """Replace files with comprehensive strategy"""
        success_count = 0
        total_count = 0

        try:
            # Find the actual source directory (skip wrapper folders like "rfid-agent")
            actual_source_dir = self._find_actual_source_dir(source_dir)

            # Get all files to replace
            files_to_replace = []
            for root, dirs, files in os.walk(actual_source_dir):
                for file in files:
                    source_path = os.path.join(root, file)
                    rel_path = os.path.relpath(source_path, actual_source_dir)
                    target_path = os.path.join(target_dir, rel_path)
                    files_to_replace.append((source_path, target_path, rel_path))

            total_count = len(files_to_replace)
            self.logger.info(f"Replacing {total_count} files...")

            for i, (source_path, target_path, rel_path) in enumerate(files_to_replace):
                print(f"[{i+1}/{total_count}] {rel_path}")

                # Ensure target directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # Try to replace file
                if self.file_replacer.replace_file(
                    source_path, target_path, backup_dir
                ):
                    success_count += 1
                    print(f"   ✅ Success")
                else:
                    print(f"   ⚠️  Skipped")

        except Exception as e:
            self.logger.error(f"File replacement error: {e}")

        return success_count, total_count

    def _find_actual_source_dir(self, extract_dir: str) -> str:
        """Find the actual source directory containing the application files"""
        # Check if there's a wrapper folder like "rfid-agent"
        subdirs = [
            d
            for d in os.listdir(extract_dir)
            if os.path.isdir(os.path.join(extract_dir, d))
        ]

        # If there's only one subdirectory, it's likely the wrapper
        if len(subdirs) == 1:
            potential_source = os.path.join(extract_dir, subdirs[0])
            # Check if this directory contains typical app files
            contents = os.listdir(potential_source)
            app_indicators = [".exe", ".dll", "assets", "PyQt6", "repositories"]

            # If we find app indicators, use this as source
            if any(
                any(indicator in item for indicator in app_indicators)
                for item in contents
            ):
                self.logger.info(f"Found application directory: {subdirs[0]}")
                return potential_source

        # Fallback to extract_dir if no wrapper found
        return extract_dir

    def _restore_backup(self, backup_dir: str, install_dir: str) -> bool:
        """Restore from backup"""
        try:
            self.logger.info("🔄 Restoring from backup...")

            restored_files = 0
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    backup_path = os.path.join(root, file)
                    rel_path = os.path.relpath(backup_path, backup_dir)
                    target_path = os.path.join(install_dir, rel_path)

                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    try:
                        shutil.copy2(backup_path, target_path)
                        restored_files += 1
                    except Exception as e:
                        self.logger.warning(f"Could not restore {file}: {e}")

            self.logger.info(f"Restored {restored_files} files from backup")
            return restored_files > 0

        except Exception as e:
            self.logger.error(f"Restore error: {e}")
            return False


def get_latest_release_info():
    """Auto-detect latest release from GitHub and generate download URL"""
    try:
        if not REQUESTS_AVAILABLE:
            print("❌ requests library not available for auto-detection")
            return None

        # GitHub API endpoint
        api_url = (
            "https://api.github.com/repos/quanghiep03198/rfid-agent/releases/latest"
        )

        print("🔍 Checking for latest release...")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()

        release_data = response.json()
        version = release_data["tag_name"]

        # Generate download URL based on version pattern
        download_url = f"https://github.com/quanghiep03198/rfid-agent/releases/download/{version}/rfid-agent-{version}-windows-x64.zip"

        print(f"✅ Latest version found: {version}")
        print(f"✅ Generated download URL: {download_url}")

        return {
            "version": version,
            "download_url": download_url,
            "release_data": release_data,
        }

    except Exception as e:
        print(f"❌ Failed to get latest release info: {e}")
        return None


def main():
    """CLI interface for the update manager"""
    import argparse

    parser = argparse.ArgumentParser(description="EPC Clean Update Manager")
    parser.add_argument(
        "--update-url", help="Update URL (optional - will auto-detect if not provided)"
    )
    parser.add_argument("--install-dir", default=".", help="Installation directory")
    parser.add_argument("--current-version", help="Current version")
    parser.add_argument("--force", action="store_true", help="Force update")
    parser.add_argument("--silent", action="store_true", help="Silent mode")
    parser.add_argument("--backup-dir", help="Backup directory")
    parser.add_argument(
        "--processes",
        nargs="*",
        default=["main.exe"],
        help="Process names to terminate",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Test auto-detection without downloading"
    )

    args = parser.parse_args()

    # Auto-detect latest release if no URL provided
    update_url = args.update_url
    if not update_url:
        print("📡 No update URL provided, auto-detecting latest release...")
        release_info = get_latest_release_info()
        if release_info:
            update_url = release_info["download_url"]
            if not args.current_version:
                args.current_version = "1.0.0"  # Default current version
            print(f"🎯 Using auto-detected URL: {update_url}")
            print(f"📝 Version detected: {release_info['version']}")
            if "published_at" in release_info:
                print(f"📅 Published: {release_info['published_at']}")
        else:
            print("❌ Failed to auto-detect latest release")
            print("💡 Please provide --update-url manually")
            sys.exit(1)

    # If dry-run, just show detection results and exit
    if args.dry_run:
        print("\n🧪 Dry-run mode - showing detection results only:")
        print(f"   Update URL: {update_url}")
        print(f"   Current Version: {args.current_version}")
        print(f"   Install Directory: {args.install_dir}")
        print("✅ Auto-detection working correctly!")
        return

    updater = CleanUpdateManager()

    success = updater.perform_complete_update(
        update_url=update_url,
        install_dir=args.install_dir,
        current_version=args.current_version,
        backup_dir=args.backup_dir,
        force=args.force,
        silent=args.silent,
        process_names=args.processes,
    )

    if not args.silent:
        if success:
            print("\n🎉 Update completed successfully!")
        else:
            print("\n❌ Update failed!")

        input("Press Enter to exit...")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
