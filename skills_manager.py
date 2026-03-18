#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能管理器 - 产品级版本

设计原则：
1. 不依赖外部命令（openclaw CLI）获取技能列表
2. 直接从配置文件和文件系统读取技能信息
3. 提供优雅降级，确保在任何环境下都能工作
4. 内置常用技能数据，确保离线可用
"""

import os
import json
import glob
from datetime import datetime, timedelta


class SkillManager:
    """技能管理器 - 产品级实现"""
    
    # 内置技能数据 - 包含所有 openclaw-bundled 和常用技能
    # 这些数据与 openclaw skills list 中的 ready 技能对应
    BUNDLED_SKILLS = [
        # openclaw-bundled 技能 (ready 状态)
        {
            "id": "weather",
            "name": "天气查询",
            "description": "获取当前天气和预报，支持 wttr.in 和 Open-Meteo。使用场景：用户询问天气、温度或预报时",
            "icon": "☔",
            "category": "tool",
            "source": "openclaw-bundled"
        },
        {
            "id": "gemini",
            "name": "Gemini",
            "description": "Gemini CLI 用于问答、摘要和生成",
            "icon": "✨",
            "category": "tool",
            "source": "openclaw-bundled"
        },
        {
            "id": "healthcheck",
            "name": "安全检查",
            "description": "主机安全加固和风险配置检查，用于安全审计、防火墙/SSH/更新加固等",
            "icon": "🔍",
            "category": "security",
            "source": "openclaw-bundled"
        },
        {
            "id": "coding-agent",
            "name": "编程助手",
            "description": "委托编码任务给 Codex、Claude Code 或 Pi 代理，支持构建新功能、审查PR、重构代码库",
            "icon": "🧩",
            "category": "dev",
            "source": "openclaw-bundled"
        },
        {
            "id": "skill-creator",
            "name": "技能创建器",
            "description": "创建、编辑和改进 AgentSkills，支持从零创建技能或重构现有技能",
            "icon": "🛠️",
            "category": "dev",
            "source": "openclaw-bundled"
        },
        {
            "id": "mcporter",
            "name": "MCP 工具",
            "description": "配置和调用 MCP 服务器/工具，支持 HTTP 和 stdio 模式",
            "icon": "🔌",
            "category": "tool",
            "source": "openclaw-bundled"
        },
        # openclaw-extra 技能
        {
            "id": "acp-router",
            "name": "ACP 路由",
            "description": "将请求路由到 Pi、Claude Code、Codex、OpenCode、Gemini CLI 等 ACP 工具",
            "icon": "📦",
            "category": "dev",
            "source": "openclaw-extra"
        },
        # openclaw-workspace 技能
        {
            "id": "github",
            "name": "GitHub",
            "description": "使用 gh CLI 与 GitHub 交互，管理 issues、PRs 和 CI 运行",
            "icon": "🐙",
            "category": "dev",
            "source": "openclaw-workspace"
        },
        {
            "id": "agent-reach",
            "name": "平台接入",
            "description": "配置 Twitter、Reddit、抖音、小红书、LinkedIn 等平台访问工具",
            "icon": "🌐",
            "category": "communication",
            "source": "openclaw-workspace"
        },
        {
            "id": "china-im-channels",
            "name": "国产IM渠道",
            "description": "集成微信（公众号/企业微信）、钉钉、飞书等国产IM平台",
            "icon": "💬",
            "category": "communication",
            "source": "openclaw-workspace"
        },
        {
            "id": "prd-writer",
            "name": "PRD生成器",
            "description": "产品经理专属工具，自动生成产品需求文档，支持 Web、App、小程序、后台系统",
            "icon": "📄",
            "category": "productivity",
            "source": "openclaw-workspace"
        },
        {
            "id": "system-designer",
            "name": "系统设计师",
            "description": "架构师专属工具，自动生成系统架构设计文档、技术选型建议、数据库 schema",
            "icon": "🏗️",
            "category": "dev",
            "source": "openclaw-workspace"
        },
        {
            "id": "test-case-generator",
            "name": "测试用例生成器",
            "description": "测试工程师专属工具，根据需求自动生成测试用例，支持功能/边界/异常测试",
            "icon": "✅",
            "category": "dev",
            "source": "openclaw-workspace"
        },
        {
            "id": "find-skills",
            "name": "技能发现",
            "description": "帮助用户发现和安装技能，当用户询问如何执行某个任务时推荐合适的技能",
            "icon": "🔍",
            "category": "tool",
            "source": "openclaw-workspace"
        },
        {
            "id": "self-improving-agent",
            "name": "自我改进",
            "description": "捕获学习和错误以持续改进，记录命令失败、用户纠正、API 错误等",
            "icon": "📈",
            "category": "tool",
            "source": "openclaw-workspace"
        },
        {
            "id": "skill-dev-assistant",
            "name": "技能开发助手",
            "description": "快速创建和开发 OpenClaw Skill，自动生成目录结构、SKILL.md、Python 脚本模板",
            "icon": "👨‍💻",
            "category": "dev",
            "source": "openclaw-workspace"
        },
        {
            "id": "tavily-search",
            "name": "Tavily搜索",
            "description": "AI优化的网页搜索，返回简洁、相关的结果",
            "icon": "🔎",
            "category": "tool",
            "source": "openclaw-workspace"
        },
        {
            "id": "agent-browser",
            "name": "浏览器自动化",
            "description": "基于 Rust 的无头浏览器自动化 CLI，支持导航、点击、输入、截图",
            "icon": "📦",
            "category": "tool",
            "source": "openclaw-workspace"
        },
        {
            "id": "wecom-auto-support",
            "name": "企业微信客服",
            "description": "企业微信自动化客服支持工具",
            "icon": "💬",
            "category": "communication",
            "source": "openclaw-workspace"
        },
        {
            "id": "acpx",
            "name": "ACP 扩展",
            "description": "OpenClaw ACP 扩展插件",
            "icon": "📦",
            "category": "dev",
            "source": "openclaw-extra"
        },
    ]
    
    # 分类映射
    CATEGORIES = {
        'tool': '工具',
        'dev': '开发',
        'productivity': '效率',
        'media': '媒体',
        'communication': '通讯',
        'security': '安全',
        'other': '其他'
    }
    
    def __init__(self, cache_dir=None):
        self._skills = None
        self._last_refresh = None
    
    def get_skills(self, force_refresh=False):
        """获取所有技能"""
        if not force_refresh and self._skills is not None:
            return self._skills
        
        self._skills = self._fetch_all_skills()
        return self._skills
    
    def _fetch_all_skills(self):
        """获取所有技能数据 - 产品级实现"""
        # 1. 从内置数据开始
        skills = {s['id']: s.copy() for s in self.BUNDLED_SKILLS}
        
        # 2. 初始化所有技能为未安装
        for skill in skills.values():
            skill['installed'] = False
            skill['version'] = '?'
        
        # 3. 获取用户已安装技能（配置文件 + workspace）
        installed_skills = self._get_installed_skills()
        for skill_id, skill_info in installed_skills.items():
            if skill_id in skills:
                # 更新已安装状态
                skills[skill_id]['installed'] = True
                skills[skill_id]['version'] = skill_info.get('version', '?')
                skills[skill_id]['source'] = skill_info.get('source', 'unknown')
            else:
                # 添加用户自定义技能
                skills[skill_id] = skill_info
        
        # 4. 将 openclaw 自带的技能（bundled 和 extra）标记为已安装
        for skill in skills.values():
            if skill.get('source') in ('openclaw-bundled', 'openclaw-extra'):
                skill['installed'] = True
                skill['version'] = 'bundled'
        
        return list(skills.values())
    
    def _get_user_home(self):
        """获取用户主目录 - 跨平台兼容"""
        # 尝试多种方式获取用户目录
        for env_var in ['USERPROFILE', 'HOME']:
            path = os.environ.get(env_var)
            if path and os.path.isdir(path):
                return path
        
        # 回退到 expanduser
        return os.path.expanduser("~")
    
    def _get_openclaw_dir(self):
        """获取 OpenClaw 配置目录"""
        home = self._get_user_home()
        return os.path.join(home, ".openclaw")
    
    def _get_installed_skills(self):
        """获取已安装技能 - 从配置文件读取"""
        skills = {}
        
        # 读取 openclaw.json 配置文件
        config_path = os.path.join(self._get_openclaw_dir(), "openclaw.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 读取 plugins.installs
                installs = config.get('plugins', {}).get('installs', {})
                for skill_id, info in installs.items():
                    skills[skill_id] = {
                        'id': skill_id,
                        'name': skill_id,
                        'description': '',
                        'version': info.get('version', '?'),
                        'icon': self._get_icon_for_skill(skill_id),
                        'category': 'other',
                        'installed': True,
                        'source': info.get('source', 'unknown'),
                        'has_update': False,
                    }
            except Exception as e:
                print(f"[警告] 读取配置失败: {e}")
        
        # 扫描 workspace skills
        workspace_dir = os.path.join(self._get_openclaw_dir(), "workspace", "skills")
        if os.path.exists(workspace_dir):
            try:
                for skill_name in os.listdir(workspace_dir):
                    skill_path = os.path.join(workspace_dir, skill_name)
                    if os.path.isdir(skill_path):
                        skill_md = os.path.join(skill_path, "SKILL.md")
                        if os.path.exists(skill_md):
                            info = self._parse_skill_md(skill_md)
                            info['id'] = skill_name
                            info['installed'] = True
                            info['source'] = 'workspace'
                            info['has_update'] = False
                            skills[skill_name] = info
            except Exception as e:
                print(f"[警告] 扫描 workspace 失败: {e}")
        
        return skills
    
    def _parse_skill_md(self, skill_md_path):
        """解析 SKILL.md 文件"""
        info = {
            'name': '',
            'description': '',
            'version': '1.0.0',
            'icon': '📦',
            'category': 'other',
            'author': '',
        }
        
        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    body = parts[2].strip()
                    
                    # 简单解析 YAML
                    for line in yaml_content.split('\n'):
                        if ':' in line and not line.strip().startswith('#'):
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == 'name':
                                info['name'] = value
                            elif key == 'description':
                                info['description'] = value
                            elif key == 'version':
                                info['version'] = value
                            elif key == 'icon':
                                info['icon'] = value
                            elif key == 'category':
                                info['category'] = value
                            elif key == 'author':
                                info['author'] = value
                    
                    # 从正文提取描述
                    if not info['description']:
                        for line in body.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                info['description'] = line[:100]
                                break
                    
                    # 从正文提取名称
                    if not info['name']:
                        for line in body.split('\n'):
                            if line.startswith('# '):
                                info['name'] = line[2:].strip()
                                break
            else:
                # 没有 frontmatter，从正文解析
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('# ') and not info['name']:
                        info['name'] = line[2:].strip()
                    elif line.strip() and not line.startswith('#') and not info['description']:
                        info['description'] = line.strip()[:100]
                        break
        except Exception as e:
            print(f"[警告] 解析 {skill_md_path} 失败: {e}")
        
        # 确保有名称
        if not info['name']:
            info['name'] = os.path.basename(os.path.dirname(skill_md_path))
        
        return info
    
    def _get_icon_for_skill(self, skill_id):
        """根据技能ID获取图标"""
        icon_map = {
            'weather': '☔',
            'github': '🐙',
            'discord': '🎮',
            'slack': '💬',
            'telegram': '✈️',
            'notion': '📝',
            'trello': '📋',
            'spotify': '🎵',
            'youtube': '📺',
            'twitter': '🐦',
            'gemini': '✨',
            'openai': '🤖',
            'healthcheck': '🔍',
            'test-case-generator': '✅',
            'prd-writer': '📄',
            'skill-creator': '🛠️',
            'acpx': '📦',
            'acp-router': '📦',
            'coding-agent': '🧩',
            'agent-reach': '🌐',
            'china-im-channels': '💬',
            'system-designer': '🏗️',
            'find-skills': '🔍',
            'self-improvement': '📈',
            'skill-dev-assistant': '👨‍💻',
            'tavily': '🔎',
            'mcporter': '🔌',
            'agent-browser': '📦',
        }
        
        for key, icon in icon_map.items():
            if key in skill_id.lower():
                return icon
        
        return '📦'
    
    def get_installed_skills(self):
        """获取已安装技能"""
        return [s for s in self.get_skills() if s.get('installed')]
    
    def get_available_skills(self):
        """获取可安装技能"""
        return [s for s in self.get_skills() if not s.get('installed')]
    
    def search_skills(self, keyword):
        """搜索技能"""
        if not keyword:
            return self.get_skills()
        
        keyword = keyword.lower()
        return [
            s for s in self.get_skills()
            if keyword in s.get('name', '').lower()
            or keyword in s.get('description', '').lower()
            or keyword in s.get('id', '').lower()
        ]
    
    def get_skills_by_category(self, category):
        """按分类获取技能"""
        if category == 'all':
            return self.get_skills()
        
        return [
            s for s in self.get_skills()
            if s.get('category') == category
        ]


# 测试
if __name__ == "__main__":
    import sys
    
    # 设置编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("="*60)
    print("Skill Manager Test")
    print("="*60)
    
    manager = SkillManager()
    
    print("\n[1] Fetching all skills...")
    skills = manager.get_skills(force_refresh=True)
    print(f"  Total: {len(skills)} skills")
    
    print("\n[2] Installed skills:")
    installed = manager.get_installed_skills()
    for skill in installed[:5]:
        icon = skill['icon'].encode('ascii', 'ignore').decode('ascii') if skill['icon'] else '[]'
        print(f"  [OK] {icon} {skill['name']} ({skill['id']}) - {skill['source']}")
    if len(installed) > 5:
        print(f"  ... and {len(installed) - 5} more")
    
    print("\n[3] Available skills:")
    available = manager.get_available_skills()
    for skill in available[:5]:
        icon = skill['icon'].encode('ascii', 'ignore').decode('ascii') if skill['icon'] else '[]'
        print(f"  [  ] {icon} {skill['name']} ({skill['id']}) - {skill['source']}")
    if len(available) > 5:
        print(f"  ... and {len(available) - 5} more")
    
    print("\n[4] Category stats:")
    from collections import Counter
    categories = Counter(s.get('category', 'other') for s in skills)
    for cat, count in categories.most_common():
        print(f"  {SkillManager.CATEGORIES.get(cat, cat)}: {count}")
    
    print("\n" + "="*60)
    print("Test completed")
    print("="*60)
