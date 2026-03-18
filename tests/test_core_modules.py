#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.test_core_modules

核心模块单元测试
"""

import os
import sys
import json
import time
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.instance_manager import (
    InstanceManager,
    InstanceInfo,
    InstanceStatus,
    InstanceType,
    ResourceUsage,
    CommandResult,
)

from core.cost_tracker import (
    CostTracker,
    CostBudget,
    CostAlertLevel,
    APICallRecord,
    CostAlert,
    ModelPricing,
)

from core.team_collab import (
    TeamCollaborationManager,
    UserRole,
    AuditAction,
    SyncStatus,
    TeamMember,
    AuditLogEntry,
    SharedSkill,
    ConfigSyncItem,
)


class TestInstanceManager(unittest.TestCase):
    """测试多实例管理模块"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = InstanceManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        self.manager.stop_monitoring()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_instance(self):
        """测试添加实例"""
        instance = InstanceInfo(
            id="test-1",
            name="测试实例",
            host="localhost",
            port=8080,
            type=InstanceType.LOCAL,
        )
        
        result = self.manager.add_instance(instance)
        self.assertTrue(result)
        
        # 验证实例已添加
        retrieved = self.manager.get_instance("test-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试实例")
    
    def test_remove_instance(self):
        """测试移除实例"""
        instance = InstanceInfo(
            id="test-2",
            name="测试实例2",
            host="localhost",
            port=8081,
            type=InstanceType.LOCAL,
        )
        
        self.manager.add_instance(instance)
        result = self.manager.remove_instance("test-2")
        self.assertTrue(result)
        
        # 验证实例已移除
        retrieved = self.manager.get_instance("test-2")
        self.assertIsNone(retrieved)
    
    def test_get_all_instances(self):
        """测试获取所有实例"""
        # 添加多个实例
        for i in range(3):
            instance = InstanceInfo(
                id=f"test-{i}",
                name=f"测试实例{i}",
                host="localhost",
                port=8080 + i,
                type=InstanceType.LOCAL,
            )
            self.manager.add_instance(instance)
        
        instances = self.manager.get_all_instances()
        self.assertEqual(len(instances), 3)
    
    def test_execute_command_local(self):
        """测试本地命令执行"""
        instance = InstanceInfo(
            id="local-test",
            name="本地测试实例",
            host="localhost",
            port=0,
            type=InstanceType.LOCAL,
        )
        
        self.manager.add_instance(instance)
        
        # 执行简单命令
        result = self.manager.execute_command("local-test", "echo 'hello world'")
        
        self.assertTrue(result.success)
        self.assertIn("hello world", result.stdout)
        self.assertEqual(result.exit_code, 0)
    
    def test_resource_usage(self):
        """测试资源使用情况"""
        instance = InstanceInfo(
            id="resource-test",
            name="资源测试实例",
            host="localhost",
            port=0,
            type=InstanceType.LOCAL,
        )
        
        self.manager.add_instance(instance)
        
        # 获取资源使用情况
        usage = self.manager.get_resource_usage("resource-test")
        
        # 即使没有 psutil，也应该返回 ResourceUsage 对象
        self.assertIsNotNone(usage)
        self.assertIsInstance(usage, ResourceUsage)


class TestCostTracker(unittest.TestCase):
    """测试成本控制模块"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = CostTracker(config_dir=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_record_call(self):
        """测试记录 API 调用"""
        cost = self.tracker.record_call(
            model="gpt-3.5-turbo",
            tokens_input=100,
            tokens_output=50,
            duration_ms=1000,
            success=True,
        )
        
        self.assertIsNotNone(cost)
        self.assertGreater(cost, 0)  # 应该有成本
    
    def test_model_pricing(self):
        """测试模型定价"""
        pricing = ModelPricing(
            model_id="gpt-3.5-turbo",
            provider="openai",
            input_price_per_1k=0.0005,
            output_price_per_1k=0.0015,
        )
        
        # 验证定价对象创建成功
        self.assertEqual(pricing.model_id, "gpt-3.5-turbo")
        self.assertEqual(pricing.provider, "openai")
        self.assertEqual(pricing.input_price_per_1k, 0.0005)
        self.assertEqual(pricing.output_price_per_1k, 0.0015)
    
    def test_budget_config(self):
        """测试预算配置"""
        config = CostBudget(
            daily_limit=10.0,
            monthly_limit=100.0,
            alert_threshold_1=0.5,
            alert_threshold_2=0.8,
            alert_threshold_3=0.95,
        )
        
        self.tracker.budget = config
        retrieved = self.tracker.budget
        
        self.assertEqual(retrieved.daily_limit, 10.0)
        self.assertEqual(retrieved.monthly_limit, 100.0)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        # 记录一些调用
        for i in range(5):
            self.tracker.record_call(
                model="gpt-3.5-turbo",
                tokens_input=100,
                tokens_output=50,
                duration_ms=1000,
                success=True,
            )
        
        stats = self.tracker.generate_daily_report()
        
        self.assertIn("total_calls", stats)
        self.assertIn("total_cost", stats)
        self.assertIn("by_model", stats)
    
    def test_generate_report(self):
        """测试生成报表"""
        # 记录一些调用
        self.tracker.record_call(
            model="gpt-3.5-turbo",
            tokens_input=100,
            tokens_output=50,
            duration_ms=1000,
            success=True,
        )
        
        # 测试日报
        report = self.tracker.generate_daily_report()
        self.assertIsInstance(report, dict)
        self.assertIn("total_calls", report)
        
        # 测试月报
        report_monthly = self.tracker.generate_monthly_report()
        self.assertIsInstance(report_monthly, dict)
        self.assertIn("total_calls", report_monthly)


class TestTeamCollaboration(unittest.TestCase):
    """测试团队协作模块"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TeamCollaborationManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_team_member_permissions(self):
        """测试团队成员权限"""
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        
        member = TeamMember(
            id="member-1",
            username="member",
            email="member@example.com",
            role=UserRole.MEMBER,
        )
        
        guest = TeamMember(
            id="guest-1",
            username="guest",
            email="guest@example.com",
            role=UserRole.GUEST,
        )
        
        # 测试管理员权限
        self.assertTrue(admin.has_permission("team_member_add"))
        self.assertTrue(admin.has_permission("config_update"))
        
        # 测试成员权限
        self.assertFalse(member.has_permission("team_member_add"))
        self.assertTrue(member.has_permission("config_view"))
        self.assertTrue(member.has_permission("skill_install"))
        
        # 测试访客权限
        self.assertFalse(guest.has_permission("skill_install"))
        self.assertTrue(guest.has_permission("config_view"))
    
    def test_login_logout(self):
        """测试登录登出"""
        member = TeamMember(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.MEMBER,
        )
        
        # 登录
        result = self.manager.login(member)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_current_user(), member)
        
        # 登出
        self.manager.logout()
        self.assertIsNone(self.manager.get_current_user())
    
    def test_add_team_member(self):
        """测试添加团队成员"""
        # 先登录为管理员
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.manager.login(admin)
        
        # 添加新成员
        new_member = TeamMember(
            id="new-member",
            username="newmember",
            email="new@example.com",
            role=UserRole.MEMBER,
        )
        
        result = self.manager.add_team_member(new_member)
        self.assertTrue(result)
        
        # 验证成员已添加
        members = self.manager.get_team_members()
        self.assertEqual(len(members), 1)

    def test_update_team_member_role(self):
        """测试更新团队成员角色"""
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.manager.login(admin)

        member = TeamMember(
            id="member-2",
            username="member2",
            email="member2@example.com",
            role=UserRole.MEMBER,
        )
        self.assertTrue(self.manager.add_team_member(member))

        ok = self.manager.update_team_member_role("member-2", UserRole.GUEST)
        self.assertTrue(ok)
        updated = [m for m in self.manager.get_team_members() if m.id == "member-2"][0]
        self.assertEqual(updated.role, UserRole.GUEST)
    
    def test_audit_log(self):
        """测试审计日志"""
        # 登录
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.manager.login(admin)
        
        # 记录操作
        entry = self.manager.log_action(
            action=AuditAction.CONFIG_UPDATE,
            target_type="config",
            target_id="test-config",
            details={"key": "value"},
        )
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action, AuditAction.CONFIG_UPDATE)
        self.assertEqual(entry.target_id, "test-config")
        
        # 查询日志
        logs = self.manager.get_audit_logs()
        self.assertEqual(len(logs), 1)
    
    def test_shared_skill(self):
        """测试共享技能"""
        # 登录
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.manager.login(admin)
        
        # 添加共享技能
        skill = SharedSkill(
            id="skill-1",
            name="测试技能",
            description="这是一个测试技能",
            version="1.0.0",
            author_id="admin-1",
            author_name="admin",
            source_url="https://example.com/skill",
            install_command="openclaw skill install test-skill",
            category="tool",
            tags=["test", "demo"],
            is_approved=True,
        )
        
        result = self.manager.add_shared_skill(skill)
        self.assertTrue(result)
        
        # 验证技能已添加
        skills = self.manager.get_shared_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "测试技能")
        
        # 搜索技能
        results = self.manager.search_shared_skills("测试")
        self.assertEqual(len(results), 1)
    
    def test_config_sync(self):
        """测试配置同步"""
        # 登录
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.manager.login(admin)
        
        # 创建临时文件
        temp_file = os.path.join(self.temp_dir, "test_config.json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"test": "data"}, f)
        
        # 注册同步文件
        item = self.manager.register_sync_file(temp_file)
        self.assertIsNotNone(item)
        self.assertEqual(item.file_path, temp_file)
        self.assertEqual(item.sync_status, SyncStatus.PENDING)
        
        # 验证同步项
        items = self.manager.get_sync_items()
        self.assertEqual(len(items), 1)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.instance_manager = InstanceManager(config_dir=self.temp_dir)
        self.cost_tracker = CostTracker(config_dir=self.temp_dir)
        self.team_manager = TeamCollaborationManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        self.instance_manager.stop_monitoring()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建团队成员
        admin = TeamMember(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        
        # 2. 登录
        self.team_manager.login(admin)
        
        # 3. 添加实例
        instance = InstanceInfo(
            id="workflow-test",
            name="工作流测试实例",
            host="localhost",
            port=8080,
            type=InstanceType.LOCAL,
        )
        self.instance_manager.add_instance(instance)
        
        # 4. 执行命令（记录审计日志）
        if self.team_manager.check_permission("instance_command"):
            result = self.instance_manager.execute_command("workflow-test", "echo 'test'")
            self.team_manager.log_action(
                action=AuditAction.INSTANCE_COMMAND,
                target_type="instance",
                target_id="workflow-test",
                details={"command": "echo 'test'", "success": result.success},
            )
        
        # 5. 记录 API 调用成本
        self.cost_tracker.record_call(
            model="gpt-3.5-turbo",
            tokens_input=100,
            tokens_output=50,
            duration_ms=1000,
            success=True,
        )
        
        # 6. 验证数据
        self.assertEqual(len(self.instance_manager.get_all_instances()), 1)
        self.assertEqual(len(self.team_manager.get_audit_logs()), 1)
        self.assertEqual(self.cost_tracker.generate_daily_report()["total_calls"], 1)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestInstanceManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCostTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestTeamCollaboration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)