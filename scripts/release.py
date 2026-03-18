#!/usr/bin/env python3
"""
Butlerclaw Release Script

Automates the release process including:
- Version bumping
- Changelog updates
- Git tagging
- Build verification
- GitHub release creation

Usage:
    python scripts/release.py [patch|minor|major]

Example:
    python scripts/release.py patch  # 2.0.0 -> 2.0.1
    python scripts/release.py minor  # 2.0.0 -> 2.1.0
    python scripts/release.py major  # 2.0.0 -> 3.0.0
"""

import os
import sys
import re
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        check=check
    )
    return result


def get_current_version():
    """Extract current version from main file."""
    content = Path("openclaw_assistant.py").read_text(encoding="utf-8")
    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return "2.0.0"


def bump_version(version, bump_type):
    """Bump version according to semver."""
    parts = version.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    return f"{major}.{minor}.{patch}"


def update_version_in_files(new_version):
    """Update version in all relevant files."""
    files_to_update = [
        "openclaw_assistant.py",
        "setup.py",
        "pyproject.toml",
    ]
    
    for filepath in files_to_update:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Update version strings
            content = re.sub(
                r'VERSION\s*=\s*["\'][^"\']+["\']',
                f'VERSION = "{new_version}"',
                content
            )
            content = re.sub(
                r'version\s*=\s*["\'][^"\']+["\']',
                f'version = "{new_version}"',
                content
            )
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"✓ Updated {filepath}")


def update_changelog(new_version):
    """Update CHANGELOG.md with new version."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    with open("CHANGELOG.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Add new version section after the Unreleased section
    new_section = f"""## [Unreleased]

### Added

### Changed

### Fixed

## [{new_version}] - {today}

### Added"""
    
    content = content.replace("## [Unreleased]", new_section)
    
    # Update comparison links at the bottom
    content = re.sub(
        r'\[Unreleased\]: https://github\.com/([^/]+)/([^/]+)/compare/v[^\.]+\.\.\.HEAD',
        f'[Unreleased]: https://github.com/\\1/\\2/compare/v{new_version}...HEAD\n[{new_version}]: https://github.com/\\1/\\2/compare/v{get_current_version()}...v{new_version}',
        content
    )
    
    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✓ Updated CHANGELOG.md")


def verify_build():
    """Run tests and verify build."""
    print("\n🔍 Running verification checks...")
    
    # Run tests
    result = run_command("python -m pytest tests/ -v", check=False)
    if result.returncode != 0:
        print("❌ Tests failed!")
        print(result.stdout)
        print(result.stderr)
        return False
    print("✓ All tests passed")
    
    # Check code style
    result = run_command("python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics", check=False)
    if result.returncode != 0:
        print("⚠️  Code style issues found")
        print(result.stdout)
    else:
        print("✓ Code style check passed")
    
    return True


def create_git_commit(version):
    """Create git commit and tag."""
    print("\n📦 Creating git commit and tag...")
    
    # Stage changes
    run_command("git add -A")
    
    # Create commit
    run_command(f'git commit -m "Release version {version}"')
    print(f"✓ Created commit for v{version}")
    
    # Create tag
    run_command(f'git tag -a v{version} -m "Release version {version}"')
    print(f"✓ Created tag v{version}")
    
    # Push to remote
    print("\n🚀 Pushing to remote...")
    run_command("git push origin main")
    run_command(f"git push origin v{version}")
    print("✓ Pushed to remote")


def main():
    parser = argparse.ArgumentParser(description="Butlerclaw Release Script")
    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Get current and new version
    current_version = get_current_version()
    new_version = bump_version(current_version, args.bump_type)
    
    print(f"🔖 Current version: {current_version}")
    print(f"🔖 New version: {new_version}")
    
    if args.dry_run:
        print("\n📝 Dry run mode - no changes made")
        return
    
    # Confirm with user
    response = input(f"\n🤔 Create release v{new_version}? [y/N]: ")
    if response.lower() != "y":
        print("❌ Aborted")
        return
    
    # Run verification
    if not args.skip_tests:
        if not verify_build():
            response = input("\n⚠️  Verification failed. Continue anyway? [y/N]: ")
            if response.lower() != "y":
                print("❌ Aborted")
                return
    
    # Update files
    print("\n📝 Updating version in files...")
    update_version_in_files(new_version)
    update_changelog(new_version)
    
    # Create git commit and tag
    create_git_commit(new_version)
    
    print(f"\n✅ Release v{new_version} created successfully!")
    print(f"\nNext steps:")
    print(f"  1. GitHub Actions will build the release automatically")
    print(f"  2. Check the release at: https://github.com/yourusername/butlerclaw/releases")
    print(f"  3. Edit the release notes if needed")


if __name__ == "__main__":
    main()
