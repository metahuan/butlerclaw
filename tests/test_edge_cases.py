#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.test_edge_cases

异常链路、边界条件测试
"""

import os
import sys
import json
import time
import tempfile
import shutil
import unittest
import threading
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.instance_manager import (
    InstanceManager, InstanceInfo, InstanceStatus, InstanceType
)
from core.cost_tracker import CostTracker, CostAlertLevel


class TestInstanceManagerEdgeCases(unittest.TestCase):
    """InstanceManager 异常链路测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = InstanceManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        self.manager.stop_monitoring()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_execute_command_instance_not_found(self):
        """测试实例不存在"""
        result = self.manager.execute_command(
            "non-existent-id",
            "echo test"
        )
        
        self.assertFalse(result.success)
        self.assertIn("不存在", result.stderr)
    
    def test_ssh_without_remote_executor(self):
        """测试未安装远程执行器时的 SSH 执行"""
        # 该用例不应进行真实网络连接；通过临时关闭远程执行器能力来模拟“未安装依赖”的场景。
        import core.instance_manager as instance_manager_mod
        old_flag = getattr(instance_manager_mod, "REMOTE_EXECUTOR_AVAILABLE", False)
        instance_manager_mod.REMOTE_EXECUTOR_AVAILABLE = False

        instance = InstanceInfo(
            id="test-ssh",
            name="SSH测试",
            host="remote.com",
            port=22,
            type=InstanceType.REMOTE_SSH,
            metadata={"ssh_user": "admin"}
        )
        self.manager.add_instance(instance)
        
        result = self.manager.execute_command("test-ssh", "ls")
        
        # 应该提示需要安装依赖
        self.assertFalse(result.success)
        self.assertIn("pip install", result.stderr)
        self.assertIn("paramiko", result.stderr)

        # 还原全局标记，避免影响其他用例
        instance_manager_mod.REMOTE_EXECUTOR_AVAILABLE = old_flag
    
    def test_concurrent_instance_operations(self):
        """测试并发实例操作"""
        errors = []
        
        def add_instances():
            try:
                for i in range(10):
                    instance = InstanceInfo(
                        id=f"concurrent-{threading.current_thread().name}-{i}",
                        name=f"并发测试{i}",
                        host="localhost",
                        port=8000 + i,
                        type=InstanceType.LOCAL,
                    )
                    self.manager.add_instance(instance)
            except Exception as e:
                errors.append(str(e))
        
        # 启动多个线程并发添加
        threads = [threading.Thread(target=add_instances, name=f"T{i}") for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该没有错误
        self.assertEqual(len(errors), 0, f"并发操作出错: {errors}")
        
        # 验证实例数量
        instances = self.manager.get_all_instances()
        self.assertGreaterEqual(len(instances), 10)


class TestCostTrackerEdgeCases(unittest.TestCase):
    """CostTracker 异常链路测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = CostTracker(config_dir=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_record_with_zero_tokens(self):
        """测试零 token 记录"""
        cost = self.tracker.record_call(
            model="gpt-4",
            tokens_input=0,
            tokens_output=0,
            success=True
        )
        
        # 应该正常处理零值
        self.assertEqual(cost, 0.0)
        self.assertGreaterEqual(len(self.tracker.get_records()), 1)
    
    def test_budget_alert_thresholds(self):
        """测试预算告警阈值"""
        # 设置预算和阈值
        self.tracker.set_budget(
            daily_limit=10.0,
            monthly_limit=100.0,
            alert_thresholds=[0.5, 0.8, 0.95]
        )
        
        budget = self.tracker.get_budget()
        self.assertEqual(budget.daily_limit, 10.0)
        self.assertEqual(budget.alert_threshold_1, 0.5)
    
    def test_persistence(self):
        """测试数据持久化"""
        # 添加记录
        for i in range(10):
            self.tracker.record_call(
                model="gpt-4",
                tokens_input=1000,
                tokens_output=500,
                success=True
            )
        
        # 验证文件存在
        records_dir = os.path.join(self.temp_dir, "cost_records")
        self.assertTrue(os.path.exists(records_dir))
        
        # 验证有文件
        files = os.listdir(records_dir)
        self.assertGreaterEqual(len(files), 1)
    
    def test_cost_trend(self):
        """测试成本趋势查询"""
        # 添加记录
        self.tracker.record_call(
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            success=True
        )
        
        # 查询趋势
        trend = self.tracker.get_cost_trend(days=7)
        self.assertIsInstance(trend, list)
        self.assertGreaterEqual(len(trend), 1)
    
    def test_top_models(self):
        """测试 Top 模型查询"""
        # 添加不同模型的记录
        for model in ["gpt-4", "claude-3", "gpt-4", "gpt-4"]:
            self.tracker.record_call(
                model=model,
                tokens_input=1000,
                tokens_output=500,
                success=True
            )
        
        # 查询 Top 模型
        top_models = self.tracker.get_top_expensive_models(limit=3)
        self.assertIsInstance(top_models, list)
        self.assertGreaterEqual(len(top_models), 1)


class TestIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.instance_manager = InstanceManager(config_dir=self.temp_dir)
        self.cost_tracker = CostTracker(config_dir=self.temp_dir)
    
    def tearDown(self):
        self.instance_manager.stop_monitoring()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cost_alert_triggers(self):
        """测试成本告警触发"""
        # 设置低预算
        self.cost_tracker.set_budget(
            daily_limit=0.001,  # 很低的预算
            monthly_limit=1.0,
            alert_thresholds=[0.1, 0.5, 0.9]
        )
        
        # 记录告警回调
        alerts_received = []
        def on_alert(alert):
            alerts_received.append(alert)
        
        self.cost_tracker.on_alert(on_alert)
        
        # 添加超出预算的记录
        self.cost_tracker.record_call(
            model="gpt-4",
            tokens_input=100000,  # 大量 token
            tokens_output=50000,
            success=True
        )
        
        # 应该有告警
        alerts = self.cost_tracker.get_alerts()
        self.assertGreaterEqual(len(alerts), 1)


def run_tests():
    """运行所有边界测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestInstanceManagerEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCostTrackerEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
