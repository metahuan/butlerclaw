#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 安全优化功能测试脚本
"""

import sys
import os
import io

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openclaw_installer_v2 import (
    get_api_key_env_var_name,
    get_api_key_from_env,
    set_api_key_to_env,
    get_api_key_secure,
    API_KEY_ENV_PREFIX
)

def test_env_var_name_generation():
    """测试 1: 环境变量名称生成"""
    print("=" * 60)
    print("Test 1: Environment Variable Name Generation")
    print("=" * 60)
    
    test_cases = [
        ('deepseek', 'OPENCLAW_API_KEY_DEEPSEEK'),
        ('moonshot', 'OPENCLAW_API_KEY_MOONSHOT'),
        ('openai', 'OPENCLAW_API_KEY_OPENAI'),
        ('alibaba', 'OPENCLAW_API_KEY_ALIBABA'),
        ('anthropic', 'OPENCLAW_API_KEY_ANTHROPIC'),
        ('google', 'OPENCLAW_API_KEY_GOOGLE'),
    ]
    
    all_passed = True
    for provider, expected in test_cases:
        result = get_api_key_env_var_name(provider)
        passed = result == expected
        status = '[PASS]' if passed else '[FAIL]'
        print(f"  {status} {provider:12} -> {result}")
        if not passed:
            print(f"         Expected: {expected}")
            all_passed = False
    
    return all_passed

def test_set_and_get_env():
    """测试 2: 设置和读取环境变量"""
    print()
    print("=" * 60)
    print("Test 2: Set and Get Environment Variable")
    print("=" * 60)
    
    test_cases = [
        ('deepseek', 'sk-deepseek-test-123'),
        ('moonshot', 'sk-moonshot-test-456'),
    ]
    
    all_passed = True
    for provider, test_key in test_cases:
        # 设置环境变量
        set_api_key_to_env(provider, test_key)
        
        # 读取环境变量
        result = get_api_key_from_env(provider)
        
        passed = result == test_key
        status = '[PASS]' if passed else '[FAIL]'
        masked = result[:10] + '...' if len(result) > 10 else result
        print(f"  {status} {provider:12} -> {masked}")
        
        if not passed:
            print(f"         Expected: {test_key[:10]}...")
            all_passed = False
    
    return all_passed

def test_priority():
    """测试 3: 安全获取优先级（环境变量 > 配置文件）"""
    print()
    print("=" * 60)
    print("Test 3: Priority Test (Env Var > Config File)")
    print("=" * 60)
    
    # 设置环境变量
    env_key = 'sk-from-env-123'
    set_api_key_to_env('deepseek', env_key)
    
    # 配置文件中的 key
    config_key = 'sk-from-config-456'
    config = {
        'models': {
            'providers': {
                'deepseek': {
                    'apiKey': config_key
                }
            }
        }
    }
    
    result = get_api_key_secure('deepseek', config)
    passed = result == env_key
    status = '[PASS]' if passed else '[FAIL]'
    
    print(f"  {status} Environment variable takes priority")
    print(f"       Env:    {env_key}")
    print(f"       Config: {config_key}")
    print(f"       Result: {result}")
    
    return passed

def test_fallback():
    """测试 4: 无环境变量时回退到配置文件"""
    print()
    print("=" * 60)
    print("Test 4: Fallback to Config File")
    print("=" * 60)
    
    # 清理环境变量
    env_var = get_api_key_env_var_name('moonshot')
    if env_var in os.environ:
        del os.environ[env_var]
    
    config_key = 'sk-config-only-789'
    config = {
        'models': {
            'providers': {
                'moonshot': {
                    'apiKey': config_key
                }
            }
        }
    }
    
    result = get_api_key_secure('moonshot', config)
    passed = result == config_key
    status = '[PASS]' if passed else '[FAIL]'
    
    print(f"  {status} Correctly fallback to config file")
    print(f"       Config: {config_key}")
    print(f"       Result: {result}")
    
    return passed

def test_empty():
    """测试 5: 两者都不存在时返回空字符串"""
    print()
    print("=" * 60)
    print("Test 5: Empty Result When Neither Exists")
    print("=" * 60)
    
    # 确保环境变量不存在
    env_var = get_api_key_env_var_name('nonexistent')
    if env_var in os.environ:
        del os.environ[env_var]
    
    result = get_api_key_secure('nonexistent', {})
    passed = result == ''
    status = '[PASS]' if passed else '[FAIL]'
    
    print(f"  {status} Returns empty string: \"{result}\"")
    
    return passed

def test_backward_compatibility():
    """测试 6: 向后兼容性（仅配置文件）"""
    print()
    print("=" * 60)
    print("Test 6: Backward Compatibility (Config File Only)")
    print("=" * 60)
    
    # 模拟旧的配置文件结构
    old_config = {
        'models': {
            'default': 'deepseek/deepseek-chat',
            'providers': {
                'deepseek': {
                    'baseUrl': 'https://api.deepseek.com/v1',
                    'apiKey': 'sk-old-config-key',
                    'api': 'openai-completions'
                }
            }
        }
    }
    
    # 清理环境变量
    env_var = get_api_key_env_var_name('deepseek')
    if env_var in os.environ:
        del os.environ[env_var]
    
    result = get_api_key_secure('deepseek', old_config)
    passed = result == 'sk-old-config-key'
    status = '[PASS]' if passed else '[FAIL]'
    
    print(f"  {status} Correctly read old config file")
    print(f"       Config API Key: sk-old-config-key")
    print(f"       Result:         {result}")
    
    return passed

def cleanup():
    """清理测试环境变量"""
    print()
    print("=" * 60)
    print("Cleanup Test Environment Variables")
    print("=" * 60)
    
    providers = ['deepseek', 'moonshot', 'openai', 'alibaba', 'nonexistent']
    for provider in providers:
        env_var = get_api_key_env_var_name(provider)
        if env_var in os.environ:
            del os.environ[env_var]
            print(f"  Cleaned: {env_var}")
    
    print("  [DONE] Cleanup completed")

def main():
    """主测试函数"""
    print()
    print("=" * 60)
    print("API Key Security Enhancement Test")
    print("=" * 60)
    print()
    
    results = []
    
    # 运行所有测试
    results.append(("Env Var Name Generation", test_env_var_name_generation()))
    results.append(("Set and Get Env Var", test_set_and_get_env()))
    results.append(("Priority Test", test_priority()))
    results.append(("Fallback Test", test_fallback()))
    results.append(("Empty Result Test", test_empty()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
    # 清理
    cleanup()
    
    # 测试报告总结
    print()
    print("=" * 60)
    print("Test Report Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = '[PASS]' if result else '[FAIL]'
        print(f"  {status} {name}")
    
    print()
    print(f"Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
