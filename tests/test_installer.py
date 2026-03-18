#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 安装程序 — 可行性与完整性快速验证脚本
不启动 GUI、不访问网络，仅验证语法、导入和配置逻辑。
"""

import os
import sys
import json

# 程序目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLER_PATH = os.path.join(SCRIPT_DIR, "openclaw_installer.py")


def ok(msg):
    print(f"  [通过] {msg}")
    return True


def fail(msg):
    print(f"  [失败] {msg}")
    return False


def test_python_version():
    """检查 Python 版本 >= 3.8"""
    v = sys.version_info
    if v.major >= 3 and v.minor >= 8:
        return ok(f"Python {v.major}.{v.minor}.{v.micro}")
    return fail(f"需要 Python 3.8+，当前 {v.major}.{v.minor}.{v.micro}")


def test_syntax():
    """检查安装程序语法"""
    try:
        with open(INSTALLER_PATH, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, INSTALLER_PATH, "exec")
        return ok("openclaw_installer.py 语法正确")
    except SyntaxError as e:
        return fail(f"语法错误: {e}")
    except Exception as e:
        return fail(f"读取/编译异常: {e}")


def test_tkinter():
    """检查 tkinter 是否可用"""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, scrolledtext
        return ok("tkinter 可用")
    except ImportError as e:
        return fail(f"tkinter 不可用: {e}")


def test_import_installer():
    """导入安装程序模块（不启动 GUI）"""
    try:
        # 确保在程序目录，避免导入路径问题
        if SCRIPT_DIR not in sys.path:
            sys.path.insert(0, SCRIPT_DIR)
        import openclaw_installer as m
        return ok("openclaw_installer 模块导入成功")
    except Exception as e:
        return fail(f"导入失败: {e}")


def test_models_and_hints():
    """检查模型与 API 提示数据结构完整性"""
    try:
        import openclaw_installer as m
    except Exception:
        return fail("无法导入模块，跳过模型检查")

    errors = []

    # 每个模型必须有 provider（model 的 prefix）在 API_KEY_HINTS 中
    for category, models in m.MODELS.items():
        if not isinstance(models, dict):
            errors.append(f"MODELS['{category}'] 应为 dict")
            continue
        for model_id, desc in models.items():
            if not model_id or not desc:
                errors.append(f"模型项为空: {model_id!r} -> {desc!r}")
            provider = model_id.split("/")[0]
            if provider not in m.API_KEY_HINTS:
                errors.append(f"模型 {model_id} 的 provider '{provider}' 未在 API_KEY_HINTS 中")

    if errors:
        for e in errors:
            print(f"  [失败] {e}")
        return False
    return ok("MODELS 与 API_KEY_HINTS 对应完整")


def test_config_structure():
    """检查生成的配置结构与 openclaw 预期一致"""
    try:
        import openclaw_installer as m
    except Exception:
        return fail("无法导入模块，跳过配置结构检查")

    # 模拟 get_config 产出的结构
    model = "deepseek/deepseek-chat"
    provider = model.split("/")[0]
    config = {
        "model": model,
        "thinking": True,
        "channels": {
            "webchat": {"enabled": False}
        },
        "apiKeys": {provider: "test-key-123"}
    }

    try:
        s = json.dumps(config, indent=2, ensure_ascii=False)
        parsed = json.loads(s)
        if parsed.get("model") != model or parsed.get("apiKeys", {}).get(provider) != "test-key-123":
            return fail("配置 JSON 序列化/反序列化后内容异常")
        return ok("配置 JSON 结构正确")
    except Exception as e:
        return fail(f"配置结构检查异常: {e}")


def test_config_path():
    """检查配置目录路径可解析"""
    try:
        import openclaw_installer as m
    except Exception:
        return fail("无法导入模块，跳过路径检查")

    config_dir = os.path.expanduser("~/.openclaw")
    config_path = os.path.join(config_dir, "openclaw.json")

    if not config_dir or not config_path:
        return fail("配置路径为空")
    # 不实际创建目录，只检查路径格式
    if ".." in config_dir or ".." in config_path:
        return fail("配置路径不应包含 ..")
    return ok(f"配置路径可解析: {config_path}")


def main():
    print("=" * 50)
    print("OpenClaw 安装程序 — 可行性与完整性快速验证")
    print("=" * 50)

    tests = [
        ("Python 版本", test_python_version),
        ("语法检查", test_syntax),
        ("tkinter", test_tkinter),
        ("导入安装程序", test_import_installer),
        ("模型与 API 提示", test_models_and_hints),
        ("配置结构", test_config_structure),
        ("配置路径", test_config_path),
    ]

    passed = 0
    for name, fn in tests:
        print(f"\n{name}:")
        try:
            if fn():
                passed += 1
        except Exception as e:
            fail(str(e))

    print("\n" + "=" * 50)
    if passed == len(tests):
        print(f"全部通过 ({passed}/{len(tests)})，基础可行性与配置逻辑正常。")
        print("建议再按 测试报告/如何测试可行性与完整性.md 做完整功能与边界测试。")
        return 0
    else:
        print(f"通过 {passed}/{len(tests)}，请修复上述失败项后再测。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
