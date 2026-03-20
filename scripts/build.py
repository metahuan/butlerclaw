#!/usr/bin/env python3
"""
Build script for Butlerclaw

Creates executable builds for all supported platforms.

Usage:
    python scripts/build.py [windows|macos|linux|all]

Example:
    python scripts/build.py windows    # Build for Windows only
    python scripts/build.py all        # Build for all platforms
"""

import os
import sys
import shutil
import subprocess
import argparse
import platform
from pathlib import Path


def clean_build_dirs():
    """Clean build directories."""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Cleaned {dir_name}/")


def build_windows():
    """Build Windows executable."""
    print("\n🔨 Building for Windows...")
    
    # Install PyInstaller if not present
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyinstaller"], check=True)
    
    # Build executable
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "openclaw_installer.spec", "--clean"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ Windows build failed!")
        print(result.stderr)
        return False
    
    print("✓ Windows build complete")
    print(f"  Output: dist/Butlerclaw龙虾管家.exe")
    return True


def build_macos():
    """Build macOS app."""
    print("\n🔨 Building for macOS...")
    
    if platform.system() != "Darwin":
        print("⚠️  macOS builds must be created on macOS")
        return False
    
    # Run build script
    result = subprocess.run(
        ["./build_macos.sh"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ macOS build failed!")
        print(result.stderr)
        return False
    
    print("✓ macOS build complete")
    print(f"  Output: dist/Butlerclaw.app")
    return True


def build_linux():
    """Build Linux executable."""
    print("\n🔨 Building for Linux...")
    
    if platform.system() != "Linux":
        print("⚠️  Linux builds must be created on Linux")
        return False
    
    # Run build script
    result = subprocess.run(
        ["./build_linux.sh"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ Linux build failed!")
        print(result.stderr)
        return False
    
    print("✓ Linux build complete")
    print(f"  Output: dist/Butlerclaw/")
    return True


def create_packages():
    """Create distribution packages."""
    print("\n📦 Creating distribution packages...")
    
    dist_dir = Path("dist")
    packages_dir = Path("packages")
    packages_dir.mkdir(exist_ok=True)
    
    # Package Windows executable
    windows_exe = dist_dir / "Butlerclaw龙虾管家.exe"
    if windows_exe.exists():
        shutil.copy(windows_exe, packages_dir / "Butlerclaw-Windows.exe")
        print("✓ Created Butlerclaw-Windows.exe")
    
    # Package macOS app
    macos_app = dist_dir / "Butlerclaw.app"
    if macos_app.exists():
        shutil.make_archive(
            str(packages_dir / "Butlerclaw-macOS"),
            "zip",
            dist_dir,
            "Butlerclaw.app"
        )
        print("✓ Created Butlerclaw-macOS.zip")
    
    # Package Linux executable
    linux_dir = dist_dir / "Butlerclaw"
    if linux_dir.exists():
        shutil.make_archive(
            str(packages_dir / "Butlerclaw-Linux"),
            "gztar",
            dist_dir,
            "Butlerclaw"
        )
        print("✓ Created Butlerclaw-Linux.tar.gz")
    
    print(f"\n📁 Packages created in: {packages_dir.absolute()}")


def verify_build():
    """Verify the build by running tests."""
    print("\n🔍 Running verification tests...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("⚠️  Some tests failed:")
        print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
        return False
    
    print("✓ All tests passed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Butlerclaw Build Script")
    parser.add_argument(
        "target",
        choices=["windows", "macos", "linux", "all"],
        help="Target platform to build for"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests"
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Create distribution packages"
    )
    
    args = parser.parse_args()
    
    # Clean if requested
    if args.clean:
        clean_build_dirs()
    
    # Run tests
    if not args.skip_tests:
        if not verify_build():
            response = input("\n⚠️  Tests failed. Continue anyway? [y/N]: ")
            if response.lower() != "y":
                print("❌ Build aborted")
                return
    
    # Build for target platform(s)
    success = True
    current_platform = platform.system()
    
    if args.target == "windows" or args.target == "all":
        if current_platform == "Windows":
            success = build_windows() and success
        else:
            print("⚠️  Skipping Windows build (must be built on Windows)")
    
    if args.target == "macos" or args.target == "all":
        if current_platform == "Darwin":
            success = build_macos() and success
        else:
            print("⚠️  Skipping macOS build (must be built on macOS)")
    
    if args.target == "linux" or args.target == "all":
        if current_platform == "Linux":
            success = build_linux() and success
        else:
            print("⚠️  Skipping Linux build (must be built on Linux)")
    
    # Create packages
    if args.package and success:
        create_packages()
    
    if success:
        print("\n✅ Build completed successfully!")
    else:
        print("\n❌ Build completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
