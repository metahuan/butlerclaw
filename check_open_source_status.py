#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开源状态检查脚本
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_DIR = Path("D:/公司产品/Butlerclaw")

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    full_path = PROJECT_DIR / filepath
    exists = full_path.exists()
    status = "[OK]" if exists else "[FAIL]"
    print(f"{status} {description}: {filepath}")
    return exists

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n[CHECK] {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR
        )
        if result.returncode == 0:
            print(f"[OK] {description} - Success")
            return True
        else:
            print(f"[FAIL] {description} - Failed")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] {description} - Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Butlerclaw Open Source Status Check")
    print("=" * 60)
    
    checks = []
    
    # 1. Check core files
    print("\n1. Core Files Check")
    checks.append(check_file_exists("README.md", "README"))
    checks.append(check_file_exists("LICENSE", "License"))
    checks.append(check_file_exists("requirements.txt", "Requirements"))
    checks.append(check_file_exists(".github/workflows/ci.yml", "CI Config"))
    
    # 2. Check Git status
    print("\n2. Git Status Check")
    has_git = (PROJECT_DIR / ".git").exists()
    if has_git:
        print("[OK] Git repository initialized")
        
        # Check remote
        result = subprocess.run(
            "git remote -v",
            shell=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR
        )
        if "github.com" in result.stdout:
            print("[OK] GitHub remote configured")
            print(f"Remote: {result.stdout.strip()}")
            checks.append(True)
        else:
            print("[FAIL] GitHub remote not configured")
            checks.append(False)
        
        # Check uncommitted changes
        result = subprocess.run(
            "git status --porcelain",
            shell=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR
        )
        if result.stdout.strip():
            print("[WARN] Uncommitted changes:")
            print(result.stdout[:500])
        else:
            print("[OK] No uncommitted changes")
    else:
        print("[FAIL] Git repository not initialized")
        checks.append(False)
    
    # 3. Check tests
    print("\n3. Test Check")
    test_passed = run_command(
        "python -m unittest tests.test_core_modules 2>&1",
        "Core module tests"
    )
    checks.append(test_passed)
    
    # 4. Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(checks)
    total = len(checks)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if percentage >= 80:
        print("[OK] Project is ready for release")
    elif percentage >= 60:
        print("[WARN] Project is usable but has issues")
    else:
        print("[FAIL] Project has serious issues")
    
    print("\nNext Steps:")
    print("1. Visit https://github.com/metahuan/butlerclaw/actions")
    print("2. Check CI/CD status")
    print("3. Create a release tag if tests pass")
    
    return 0 if percentage >= 60 else 1

if __name__ == "__main__":
    sys.exit(main())
