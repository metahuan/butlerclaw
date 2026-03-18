#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClawHub API 客户端

用于从 clawhub.ai 获取技能信息
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ClawHubSkill:
    """ClawHub 技能信息"""
    id: str
    name: str
    description: str
    author: str
    version: str
    downloads: int
    stars: int
    rating: float
    rating_count: int
    category: str
    tags: List[str]
    icon: str
    updated_at: str
    source_url: str
    documentation_url: str
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "downloads": self.downloads,
            "stars": self.stars,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "category": self.category,
            "tags": self.tags,
            "icon": self.icon,
            "updated_at": self.updated_at,
            "source_url": self.source_url,
            "documentation_url": self.documentation_url,
            "meta": {
                "downloads": self._format_number(self.downloads),
                "stars": self.stars,
                "rating": f"{self.rating:.1f}",
                "author": self.author,
                "updated": self.updated_at
            }
        }
    
    @staticmethod
    def _format_number(n: int) -> str:
        """格式化数字（如 1234567 -> 1.2M）"""
        if n >= 1000000:
            return f"{n/1000000:.1f}M"
        elif n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)


class ClawHubAPI:
    """ClawHub API 客户端"""
    
    # API 基础URL（根据实际API文档调整）
    BASE_URL = "https://api.clawhub.ai/v1"
    # 或者使用网页抓取方式
    WEB_URL = "https://clawhub.ai"
    
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self._cache = {}
        self._cache_ttl = 3600  # 1小时缓存
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        发送 API 请求
        
        注意：这里使用模拟数据，实际使用时需要替换为真实的API调用
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            "User-Agent": "OpenClaw-Butler/1.0",
            "Accept": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code} - {e.reason}")
            return {}
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
            return {}
        except Exception as e:
            print(f"Request Error: {e}")
            return {}
    
    def get_popular_skills(self, limit: int = 50) -> List[ClawHubSkill]:
        """
        获取热门技能
        
        实际API端点可能为：/skills/popular 或 /skills?sort=downloads
        """
        # 模拟API响应
        # 实际使用时替换为：data = self._make_request("skills/popular", {"limit": limit})
        
        # 返回模拟数据
        mock_data = self._get_mock_popular_skills(limit)
        return [ClawHubSkill(**skill) for skill in mock_data]
    
    def search_skills(self, query: str, limit: int = 20) -> List[ClawHubSkill]:
        """
        搜索技能
        
        实际API端点可能为：/skills/search?q={query}
        """
        # 模拟API响应
        # 实际使用时替换为：data = self._make_request("skills/search", {"q": query, "limit": limit})
        
        # 返回模拟数据（过滤包含query的技能）
        all_skills = self._get_mock_all_skills()
        filtered = [
            skill for skill in all_skills
            if query.lower() in skill["name"].lower() 
            or query.lower() in skill["description"].lower()
            or query.lower() in skill.get("tags", [])
        ]
        return [ClawHubSkill(**skill) for skill in filtered[:limit]]
    
    def get_skill_details(self, skill_id: str) -> Optional[ClawHubSkill]:
        """
        获取技能详情
        
        实际API端点可能为：/skills/{skill_id}
        """
        # 模拟API响应
        # 实际使用时替换为：data = self._make_request(f"skills/{skill_id}")
        
        all_skills = self._get_mock_all_skills()
        for skill in all_skills:
            if skill["id"] == skill_id:
                return ClawHubSkill(**skill)
        return None
    
    def get_trending_skills(self, limit: int = 10) -> List[ClawHubSkill]:
        """
        获取 trending 技能（最近7天下载量增长最快的）
        
        实际API端点可能为：/skills/trending
        """
        # 模拟API响应
        mock_data = self._get_mock_trending_skills(limit)
        return [ClawHubSkill(**skill) for skill in mock_data]
    
    def get_new_skills(self, limit: int = 10) -> List[ClawHubSkill]:
        """
        获取最新发布的技能
        
        实际API端点可能为：/skills/new
        """
        # 模拟API响应
        mock_data = self._get_mock_new_skills(limit)
        return [ClawHubSkill(**skill) for skill in mock_data]
    
    def get_skills_by_category(self, category: str, limit: int = 20) -> List[ClawHubSkill]:
        """
        按分类获取技能
        
        实际API端点可能为：/skills?category={category}
        """
        all_skills = self._get_mock_all_skills()
        filtered = [
            skill for skill in all_skills
            if skill.get("category") == category
        ]
        return [ClawHubSkill(**skill) for skill in filtered[:limit]]
    
    def get_skill_readme(self, skill_id: str) -> str:
        """
        获取技能的 README 内容
        
        实际API端点可能为：/skills/{skill_id}/readme
        """
        # 模拟返回 README
        return f"# {skill_id}\n\nThis is the README for {skill_id}."
    
    # ========== 模拟数据（实际使用时删除）==========
    
    def _get_mock_popular_skills(self, limit: int) -> List[Dict]:
        """模拟热门技能数据"""
        skills = [
            {
                "id": "skill-vetter",
                "name": "Skill Vetter",
                "description": "Security-first skill vetting tool for OpenClaw",
                "author": "@spclaudehome",
                "version": "1.2.0",
                "downloads": 77200,
                "stars": 298,
                "rating": 4.8,
                "rating_count": 156,
                "category": "security",
                "tags": ["security", "audit", "vetting"],
                "icon": "🔐",
                "updated_at": "2026-03-10",
                "source_url": "https://github.com/spclaudehome/skill-vetter",
                "documentation_url": "https://clawhub.ai/spclaudehome/skill-vetter"
            },
            {
                "id": "playwright-mcp",
                "name": "Playwright MCP",
                "description": "Browser automation with Playwright Model Context Protocol",
                "author": "@Spiceman161",
                "version": "2.1.0",
                "downloads": 20800,
                "stars": 79,
                "rating": 4.9,
                "rating_count": 42,
                "category": "tool",
                "tags": ["browser", "automation", "playwright"],
                "icon": "🎭",
                "updated_at": "2026-03-08",
                "source_url": "https://github.com/Spiceman161/playwright-mcp",
                "documentation_url": "https://clawhub.ai/Spiceman161/playwright-mcp"
            },
            {
                "id": "api-gateway",
                "name": "API Gateway",
                "description": "Connect to 100+ APIs including Google Workspace, Microsoft 365, GitHub, Notion, Slack",
                "author": "@byungkyu",
                "version": "1.5.0",
                "downloads": 41300,
                "stars": 125,
                "rating": 4.7,
                "rating_count": 89,
                "category": "tool",
                "tags": ["api", "integration", "gateway"],
                "icon": "🌐",
                "updated_at": "2026-03-05",
                "source_url": "https://github.com/byungkyu/api-gateway-skill",
                "documentation_url": "https://clawhub.ai/byungkyu/api-gateway"
            },
            {
                "id": "ontology",
                "name": "Ontology",
                "description": "Structured knowledge graph for managing entities like Person, Project, Task, Event, Document",
                "author": "@sundial-org",
                "version": "1.3.0",
                "downloads": 98600,
                "stars": 312,
                "rating": 4.6,
                "rating_count": 178,
                "category": "productivity",
                "tags": ["knowledge", "graph", "ontology"],
                "icon": "📊",
                "updated_at": "2026-03-01",
                "source_url": "https://github.com/sundial-org/awesome-openclaw-skills",
                "documentation_url": "https://clawhub.ai/sundial-org/ontology"
            },
            {
                "id": "brave-search",
                "name": "Brave Search",
                "description": "AI-optimized web search via Brave Search API, lightweight alternative to Tavily",
                "author": "@openclaw",
                "version": "1.1.0",
                "downloads": 37300,
                "stars": 98,
                "rating": 4.5,
                "rating_count": 67,
                "category": "tool",
                "tags": ["search", "web", "brave"],
                "icon": "🔍",
                "updated_at": "2026-02-28",
                "source_url": "https://github.com/openclaw/brave-search-skill",
                "documentation_url": "https://clawhub.ai/openclaw/brave-search"
            },
            {
                "id": "summarize",
                "name": "Summarize",
                "description": "Summarize or extract text/transcripts from URLs, podcasts, and local files",
                "author": "@openclaw",
                "version": "2.0.0",
                "downloads": 143000,
                "stars": 456,
                "rating": 4.8,
                "rating_count": 234,
                "category": "productivity",
                "tags": ["summary", "text", "transcription"],
                "icon": "📝",
                "updated_at": "2026-03-12",
                "source_url": "https://github.com/openclaw/summarize-skill",
                "documentation_url": "https://clawhub.ai/openclaw/summarize"
            },
            {
                "id": "self-improving-agent",
                "name": "Self Improvement",
                "description": "Capture learnings, errors, and corrections to enable continuous improvement",
                "author": "@openclaw",
                "version": "1.8.0",
                "downloads": 191000,
                "stars": 623,
                "rating": 4.9,
                "rating_count": 412,
                "category": "tool",
                "tags": ["learning", "improvement", "memory"],
                "icon": "📈",
                "updated_at": "2026-03-11",
                "source_url": "https://github.com/openclaw/self-improving-agent",
                "documentation_url": "https://clawhub.ai/openclaw/self-improving-agent"
            },
            {
                "id": "github",
                "name": "GitHub",
                "description": "Interact with GitHub using the gh CLI for issues, PRs, CI runs, and advanced queries",
                "author": "@openclaw",
                "version": "2.5.0",
                "downloads": 102000,
                "stars": 389,
                "rating": 4.7,
                "rating_count": 267,
                "category": "dev",
                "tags": ["github", "git", "version-control"],
                "icon": "🐙",
                "updated_at": "2026-03-09",
                "source_url": "https://github.com/openclaw/github-skill",
                "documentation_url": "https://clawhub.ai/openclaw/github"
            },
        ]
        return skills[:limit]
    
    def _get_mock_all_skills(self) -> List[Dict]:
        """获取所有模拟技能"""
        return self._get_mock_popular_skills(100)
    
    def _get_mock_trending_skills(self, limit: int) -> List[Dict]:
        """模拟 trending 技能"""
        skills = self._get_mock_popular_skills(100)
        # 按下载量排序，模拟 trending
        skills.sort(key=lambda x: x["downloads"], reverse=True)
        return skills[:limit]
    
    def _get_mock_new_skills(self, limit: int) -> List[Dict]:
        """模拟新技能"""
        skills = self._get_mock_popular_skills(100)
        # 按更新时间排序
        skills.sort(key=lambda x: x["updated_at"], reverse=True)
        return skills[:limit]


# 便捷函数
def get_clawhub_skills(limit: int = 50) -> List[Dict]:
    """获取 ClawHub 技能的便捷函数"""
    api = ClawHubAPI()
    skills = api.get_popular_skills(limit)
    return [skill.to_dict() for skill in skills]


def search_clawhub_skills(query: str, limit: int = 20) -> List[Dict]:
    """搜索 ClawHub 技能的便捷函数"""
    api = ClawHubAPI()
    skills = api.search_skills(query, limit)
    return [skill.to_dict() for skill in skills]
