#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证技能安装优化模块集成
"""

import sys
import os
import io

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_install_queue():
    """测试安装队列管理器"""
    print("=" * 60)
    print("测试 1: 安装队列管理器")
    print("=" * 60)
    
    try:
        from skills.install_queue import InstallQueueManager
        
        manager = InstallQueueManager(max_concurrent=1)
        
        # 添加任务
        task = manager.add_task("test-skill", skill_name="Test Skill", priority=5)
        print(f"[PASS] 任务创建成功: {task.id}")
        print(f"[PASS] 任务状态: {task.status.value}")
        
        # 获取统计
        stats = manager.get_stats()
        print(f"[PASS] 队列统计: 总计={stats.total}, 等待中={stats.pending}")
        
        # 启动和停止
        manager.start()
        print("[PASS] 队列管理器启动成功")
        manager.stop()
        print("[PASS] 队列管理器停止成功")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_checker():
    """测试依赖检查器"""
    print()
    print("=" * 60)
    print("测试 2: 依赖检查器")
    print("=" * 60)
    
    try:
        from skills.dependency_checker import DependencyChecker
        
        checker = DependencyChecker()
        
        # 检查依赖
        report = checker.check_before_install("skill-vetter")
        
        print(f"[PASS] 依赖检查完成")
        print(f"[PASS] 是否可以安装: {report.can_install}")
        print(f"[PASS] 检查项数: {len(report.checks)}")
        print(f"[PASS] 可自动修复: {len(report.auto_fixable)}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handler():
    """测试错误处理器"""
    print()
    print("=" * 60)
    print("测试 3: 错误处理器")
    print("=" * 60)
    
    try:
        from skills.error_handler import InstallErrorHandler
        
        handler = InstallErrorHandler()
        
        # 测试错误分析
        error_output = "fatal: unable to access: Rate limit exceeded"
        
        analysis = handler.analyze_error(error_output, skill_id="skill-vetter")
        
        print(f"[PASS] 错误类型: {analysis.error_type.value}")
        print(f"[PASS] 错误消息: {analysis.message}")
        print(f"[PASS] 解决方案: {len(analysis.solutions)} 个")
        
        # 测试重试策略
        should_retry, delay = handler.should_retry(error_output, retry_count=0)
        
        print(f"[PASS] 应重试: {should_retry}, 延迟: {delay}秒")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_offline_installer():
    """测试离线安装器"""
    print()
    print("=" * 60)
    print("测试 4: 离线安装器")
    print("=" * 60)
    
    try:
        from skills.error_handler import OfflineInstaller
        
        installer = OfflineInstaller()
        
        # 测试导出功能（不需要实际文件）
        print("[PASS] 离线安装器初始化成功")
        
        # 测试方法存在
        assert hasattr(installer, 'install_from_file')
        assert hasattr(installer, 'export_skill_package')
        assert hasattr(installer, 'create_offline_bundle')
        print("[PASS] 所有方法存在")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skills_panel_integration():
    """测试 SkillsPanel 集成"""
    print()
    print("=" * 60)
    print("测试 5: SkillsPanel 集成")
    print("=" * 60)
    
    try:
        import tkinter as tk
        from tkinter import ttk
        from openclaw_assistant import SkillsPanel
        
        # 创建模拟app
        class MockApp:
            pass
        
        # 创建根窗口
        root = tk.Tk()
        root.withdraw()
        
        # 尝试创建 SkillsPanel
        panel = SkillsPanel(root, MockApp())
        print("[PASS] SkillsPanel 初始化成功")
        
        # 检查安装优化是否启用
        if hasattr(panel, '_install_optimization_enabled'):
            print(f"[PASS] 安装优化启用状态: {panel._install_optimization_enabled}")
        
        # 检查队列管理器是否存在
        if hasattr(panel, '_queue_manager'):
            print("[PASS] 队列管理器已集成")
        
        # 检查依赖检查器是否存在
        if hasattr(panel, '_dependency_checker'):
            print("[PASS] 依赖检查器已集成")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenClaw Butler - 技能安装优化模块集成测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("安装队列管理器", test_install_queue()))
    results.append(("依赖检查器", test_dependency_checker()))
    results.append(("错误处理器", test_error_handler()))
    results.append(("离线安装器", test_offline_installer()))
    results.append(("SkillsPanel 集成", test_skills_panel_integration()))
    
    # 打印结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print()
    print(f"Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
