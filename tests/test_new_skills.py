#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的技能管理模块
"""

import sys
sys.path.insert(0, r'E:\公司包包\openclaw行程文件\openclaw安装程序')

print('='*70)
print('OpenClaw 技能管理模块 - 重新设计测试')
print('='*70)

# 测试1: 语法检查
print('\n[1] 语法检查')
try:
    with open(r'E:\公司包包\openclaw行程文件\openclaw安装程序\skills_panel_new.py', 'r', encoding='utf-8') as f:
        code = f.read()
    compile(code, 'skills_panel_new.py', 'exec')
    print('  [OK] skills_panel_new.py 语法正确')
except Exception as e:
    print(f'  [FAIL] 语法错误: {e}')

# 测试2: 模块导入
print('\n[2] 模块导入测试')
try:
    from skills_panel_new import (
        SkillCard, 
        SkillDetailPanel, 
        SkillsPanelNew,
        SKILL_CATEGORIES,
        CONFIG_PATH
    )
    print('  [OK] 所有类导入成功')
    print(f'  [INFO] 分类定义: {len(SKILL_CATEGORIES)} 个')
    for k, v in SKILL_CATEGORIES.items():
        print(f'    - {k}: {v}')
except Exception as e:
    print(f'  [FAIL] 导入失败: {e}')
    import traceback
    traceback.print_exc()

# 测试3: 配置检查
print('\n[3] 配置检查')
import os
if os.path.exists(CONFIG_PATH):
    print(f'  [OK] 配置文件存在: {CONFIG_PATH}')
    try:
        import json
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        plugins = config.get('plugins', {}).get('installs', {})
        print(f'  [INFO] 已安装技能: {len(plugins)} 个')
        for skill_id in plugins.keys():
            print(f'    - {skill_id}')
    except Exception as e:
        print(f'  [WARN] 读取配置失败: {e}')
else:
    print(f'  [WARN] 配置文件不存在: {CONFIG_PATH}')

# 测试4: CLI 检查
print('\n[4] CLI 检查')
import subprocess
try:
    r = subprocess.run('openclaw --version', shell=True, capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        print(f'  [OK] OpenClaw CLI: {r.stdout.strip()}')
    else:
        print('  [WARN] CLI 可能未正确安装')
except Exception as e:
    print(f'  [WARN] 无法检测 CLI: {e}')

# 测试5: 技能列表获取
print('\n[5] 技能列表获取测试')
try:
    r = subprocess.run('openclaw skills list', shell=True, capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        lines = r.stdout.strip().split('\n') if r.stdout else []
        print(f'  [OK] 获取到 {len(lines)} 行数据')
        if lines:
            print(f'  [INFO] 前3行示例:')
            for line in lines[:3]:
                print(f'    {line[:60]}...' if len(line) > 60 else f'    {line}')
    else:
        err_msg = r.stderr[:100] if r.stderr else "未知错误"
        print(f'  [WARN] CLI 返回错误: {err_msg}')
except Exception as e:
    print(f'  [WARN] 获取失败: {e}')

print('\n' + '='*70)
print('测试总结')
print('='*70)
print('''
新技能管理模块改进点:

1. 布局改进:
   ✅ 左右分栏: 列表区 + 详情区
   ✅ 已安装/可安装分区显示
   ✅ 搜索框 + 分类筛选

2. 交互改进:
   ✅ 点击技能卡片显示详情
   ✅ 明确的安装/卸载/更新按钮
   ✅ 实时操作日志

3. 功能改进:
   ✅ 技能搜索过滤
   ✅ 分类筛选 (全部/工具/开发/效率/媒体/其他)
   ✅ 版本更新标记
   ✅ 技能详情展示

待完善:
   - 技能图标和元数据需要从 CLI 获取更完整信息
   - 批量操作功能
   - 技能评分和下载量显示
''')
print('='*70)
