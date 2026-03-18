#!/usr/bin/env python3
"""
Version management script for Butlerclaw

Usage:
    python scripts/version.py [get|set|bump] [args]

Commands:
    get              - Get current version
    set <version>    - Set version to specific value
    bump <type>      - Bump version (patch|minor|major)

Examples:
    python scripts/version.py get
    python scripts/version.py set 2.1.0
    python scripts/version.py bump patch
"""

import os
import sys
import re
import argparse
from pathlib import Path


def get_version_from_file(filepath):
    """Extract version from a file."""
    if not os.path.exists(filepath):
        return None
    
    content = Path(filepath).read_text(encoding="utf-8")
    
    # Try different patterns
    patterns = [
        r'VERSION\s*=\s*["\']([^"\']+)["\']',
        r'version\s*=\s*["\']([^"\']+)["\']',
        r'"version":\s*"([^"]+)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    
    return None


def get_current_version():
    """Get current version from main files."""
    files_to_check = [
        "openclaw_assistant.py",
        "setup.py",
        "pyproject.toml",
        "package.json",
    ]
    
    for filepath in files_to_check:
        version = get_version_from_file(filepath)
        if version:
            return version
    
    return "2.0.0"


def bump_version(version, bump_type):
    """Bump version according to semver."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    return f"{major}.{minor}.{patch}"


def update_version_in_files(new_version):
    """Update version in all relevant files."""
    files_patterns = [
        ("openclaw_assistant.py", r'VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{new_version}"'),
        ("setup.py", r'version\s*=\s*["\'][^"\']+["\']', f'version="{new_version}"'),
        ("pyproject.toml", r'version\s*=\s*["\'][^"\']+["\']', f'version = "{new_version}"'),
    ]
    
    updated_files = []
    
    for filepath, pattern, replacement in files_patterns:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = re.sub(pattern, replacement, content)
            
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                updated_files.append(filepath)
    
    return updated_files


def main():
    parser = argparse.ArgumentParser(description="Butlerclaw Version Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Get command
    subparsers.add_parser("get", help="Get current version")
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set version")
    set_parser.add_argument("version", help="Version to set (e.g., 2.1.0)")
    
    # Bump command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
        "type",
        choices=["patch", "minor", "major"],
        help="Type of version bump"
    )
    
    args = parser.parse_args()
    
    if args.command == "get" or args.command is None:
        version = get_current_version()
        print(version)
    
    elif args.command == "set":
        # Validate version format
        if not re.match(r'^\d+\.\d+\.\d+$', args.version):
            print(f"Error: Invalid version format: {args.version}", file=sys.stderr)
            print("Version must be in format: X.Y.Z (e.g., 2.1.0)", file=sys.stderr)
            sys.exit(1)
        
        updated = update_version_in_files(args.version)
        print(f"✓ Version set to {args.version}")
        if updated:
            print(f"  Updated files: {', '.join(updated)}")
    
    elif args.command == "bump":
        current = get_current_version()
        new_version = bump_version(current, args.type)
        updated = update_version_in_files(new_version)
        print(f"✓ Version bumped: {current} → {new_version}")
        if updated:
            print(f"  Updated files: {', '.join(updated)}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
