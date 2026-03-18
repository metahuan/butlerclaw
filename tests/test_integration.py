#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证健康度评分系统集成
"""

import sys
import os
import io

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_health_score():
    """测试健康度评分系统"""
    print("=" * 60)
    print("测试 1: 健康度评分系统")
    print("=" * 60)
    
    try:
        from diagnose.health_score import HealthScoreCalculator, HealthScoreHistory
        
        # 创建计算器
        calculator = HealthScoreCalculator()
        
        # 模拟诊断结果
        results = [
            {"name": "Node.js", "status": "pass", "category": "environment", "weight": 10},
            {"name": "npm", "status": "pass", "category": "environment", "weight": 10},
            {"name": "OpenClaw CLI", "status": "pass", "category": "tools", "weight": 10},
            {"name": "Config", "status": "warn", "category": "configuration", "weight": 5, "message": "发现未知键"},
            {"name": "API Key", "status": "pass", "category": "security", "weight": 10},
        ]
        
        # 计算评分
        score_result = calculator.calculate(results)
        
        print(f"[PASS] 健康度评分: {score_result.total_score}分")
        print(f"[PASS] 等级: {score_result.grade.grade} - {score_result.grade.label}")
        print(f"[PASS] 分类数: {len(score_result.categories)}")
        print(f"[PASS] 建议数: {len(score_result.recommendations)}")
        
        # 测试历史记录
        history = HealthScoreHistory()
        history.save(score_result)
        
        trend = history.get_trend(days=30)
        print(f"[PASS] 历史记录保存成功，趋势数据: {len(trend)} 条")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smart_fix():
    """测试智能修复助手"""
    print()
    print("=" * 60)
    print("测试 2: 智能修复助手")
    print("=" * 60)
    
    try:
        from diagnose.smart_fix import SmartFixAssistant
        
        assistant = SmartFixAssistant()
        
        # 测试配置问题
        issue = {
            "name": "Config Error",
            "status": "fail",
            "message": "models 包含未识别键: default, thinking",
            "category": "configuration"
        }
        
        result = assistant.analyze_and_fix(issue)
        
        print(f"[PASS] 问题分析: {result.message}")
        print(f"[PASS] 修复级别: {result.level.value}")
        print(f"[PASS] 需要重启: {result.requires_restart}")
        
        # 测试生成修复脚本
        issues = [issue]
        script = assistant.generate_fix_script(issues, platform="windows")
        
        print(f"[PASS] 修复脚本生成成功，长度: {len(script)} 字符")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_install_queue():
    """测试安装队列管理器"""
    print()
    print("=" * 60)
    print("测试 3: 安装队列管理器")
    print("=" * 60)
    
    try:
        from skills.install_queue import InstallQueueManager
        
        manager = InstallQueueManager(max_concurrent=1)
        
        # 添加任务
        task = manager.add_task("test-skill", skill_name="Test Skill", priority=5)
        
        print(f"✅ 任务创建成功: {task.id}")
        print(f"✅ 任务状态: {task.status.value}")
        
        # 获取统计
        stats = manager.get_stats()
        
        print(f"✅ 队列统计: 总计={stats.total}, 等待中={stats.pending}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_checker():
    """测试依赖检查器"""
    print()
    print("=" * 60)
    print("测试 4: 依赖检查器")
    print("=" * 60)
    
    try:
        from skills.dependency_checker import DependencyChecker
        
        checker = DependencyChecker()
        
        # 检查依赖
        report = checker.check_before_install("skill-vetter")
        
        print(f"✅ 依赖检查完成")
        print(f"✅ 是否可以安装: {report.can_install}")
        print(f"✅ 检查项数: {len(report.checks)}")
        print(f"✅ 可自动修复: {len(report.auto_fixable)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handler():
    """测试错误处理器"""
    print()
    print("=" * 60)
    print("测试 5: 错误处理器")
    print("=" * 60)
    
    try:
        from skills.error_handler import InstallErrorHandler
        
        handler = InstallErrorHandler()
        
        # 测试错误分析
        error_output = "fatal: unable to access: Rate limit exceeded"
        
        analysis = handler.analyze_error(error_output, skill_id="skill-vetter")
        
        print(f"✅ 错误类型: {analysis.error_type.value}")
        print(f"✅ 错误消息: {analysis.message}")
        print(f"✅ 解决方案: {len(analysis.solutions)} 个")
        
        # 测试重试策略
        should_retry, delay = handler.should_retry(error_output, retry_count=0)
        
        print(f"✅ 应重试: {should_retry}, 延迟: {delay}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenClaw Butler - 优化模块集成测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("健康度评分系统", test_health_score()))
    results.append(("智能修复助手", test_smart_fix()))
    results.append(("安装队列管理器", test_install_queue()))
    results.append(("依赖检查器", test_dependency_checker()))
    results.append(("错误处理器", test_error_handler()))
    
    # 打印结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {name}")
    
    print()
    print(f"总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！优化模块集成成功。")
        return 0
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
