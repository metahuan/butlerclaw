#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能数据缓存管理器

用于本地缓存 ClawHub 技能数据，提高加载速度并支持离线使用
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class SkillCacheManager:
    """技能数据缓存管理器"""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.openclaw/cache")
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存文件路径
        self.skills_cache_file = os.path.join(cache_dir, "skills_cache.json")
        self.popular_cache_file = os.path.join(cache_dir, "popular_cache.json")
        self.trending_cache_file = os.path.join(cache_dir, "trending_cache.json")
        self.new_cache_file = os.path.join(cache_dir, "new_cache.json")
        
        # 缓存有效期（秒）
        self.cache_ttl = {
            "skills": 3600,      # 1小时
            "popular": 1800,     # 30分钟
            "trending": 600,     # 10分钟
            "new": 1800          # 30分钟
        }
    
    def _is_cache_valid(self, cache_file: str, ttl: int) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_file):
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cached_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
            return (datetime.now() - cached_time).seconds < ttl
        except Exception:
            return False
    
    def _read_cache(self, cache_file: str) -> Optional[List[Dict]]:
        """读取缓存"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('skills', [])
        except Exception:
            return None
    
    def _write_cache(self, cache_file: str, skills: List[Dict]):
        """写入缓存"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'skills': skills
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入缓存失败: {e}")
    
    def get_skills(self, force_refresh: bool = False) -> List[Dict]:
        """获取所有技能（从缓存或远程）"""
        if not force_refresh and self._is_cache_valid(
            self.skills_cache_file, self.cache_ttl["skills"]
        ):
            skills = self._read_cache(self.skills_cache_file)
            if skills:
                return skills
        
        # 从远程获取
        try:
            from clawhub_api import ClawHubAPI
            api = ClawHubAPI()
            skills_data = api.get_popular_skills(limit=100)
            skills = [skill.to_dict() for skill in skills_data]
            
            # 写入缓存
            self._write_cache(self.skills_cache_file, skills)
            return skills
        except Exception as e:
            print(f"从远程获取技能失败: {e}")
            # 返回缓存数据（即使已过期）
            return self._read_cache(self.skills_cache_file) or []
    
    def get_popular_skills(self, force_refresh: bool = False) -> List[Dict]:
        """获取热门技能"""
        if not force_refresh and self._is_cache_valid(
            self.popular_cache_file, self.cache_ttl["popular"]
        ):
            skills = self._read_cache(self.popular_cache_file)
            if skills:
                return skills
        
        try:
            from clawhub_api import ClawHubAPI
            api = ClawHubAPI()
            skills_data = api.get_popular_skills(limit=20)
            skills = [skill.to_dict() for skill in skills_data]
            
            self._write_cache(self.popular_cache_file, skills)
            return skills
        except Exception as e:
            print(f"获取热门技能失败: {e}")
            return self._read_cache(self.popular_cache_file) or []
    
    def get_trending_skills(self, force_refresh: bool = False) -> List[Dict]:
        """获取 trending 技能"""
        if not force_refresh and self._is_cache_valid(
            self.trending_cache_file, self.cache_ttl["trending"]
        ):
            skills = self._read_cache(self.trending_cache_file)
            if skills:
                return skills
        
        try:
            from clawhub_api import ClawHubAPI
            api = ClawHubAPI()
            skills_data = api.get_trending_skills(limit=10)
            skills = [skill.to_dict() for skill in skills_data]
            
            self._write_cache(self.trending_cache_file, skills)
            return skills
        except Exception as e:
            print(f"获取 trending 技能失败: {e}")
            return self._read_cache(self.trending_cache_file) or []
    
    def get_new_skills(self, force_refresh: bool = False) -> List[Dict]:
        """获取新技能"""
        if not force_refresh and self._is_cache_valid(
            self.new_cache_file, self.cache_ttl["new"]
        ):
            skills = self._read_cache(self.new_cache_file)
            if skills:
                return skills
        
        try:
            from clawhub_api import ClawHubAPI
            api = ClawHubAPI()
            skills_data = api.get_new_skills(limit=10)
            skills = [skill.to_dict() for skill in skills_data]
            
            self._write_cache(self.new_cache_file, skills)
            return skills
        except Exception as e:
            print(f"获取新技能失败: {e}")
            return self._read_cache(self.new_cache_file) or []
    
    def search_skills(self, query: str) -> List[Dict]:
        """搜索技能（优先本地缓存，否则远程搜索）"""
        # 先从本地缓存搜索
        all_skills = self.get_skills(force_refresh=False)
        local_results = [
            skill for skill in all_skills
            if query.lower() in skill.get('name', '').lower()
            or query.lower() in skill.get('description', '').lower()
            or any(query.lower() in tag.lower() for tag in skill.get('tags', []))
        ]
        
        if local_results:
            return local_results
        
        # 本地没有，从远程搜索
        try:
            from clawhub_api import ClawHubAPI
            api = ClawHubAPI()
            skills_data = api.search_skills(query, limit=20)
            return [skill.to_dict() for skill in skills_data]
        except Exception as e:
            print(f"远程搜索失败: {e}")
            return []
    
    def clear_cache(self):
        """清除所有缓存"""
        for cache_file in [
            self.skills_cache_file,
            self.popular_cache_file,
            self.trending_cache_file,
            self.new_cache_file
        ]:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception:
                    pass
    
    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        info = {}
        
        for name, cache_file in [
            ("skills", self.skills_cache_file),
            ("popular", self.popular_cache_file),
            ("trending", self.trending_cache_file),
            ("new", self.new_cache_file)
        ]:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    cached_time = datetime.fromisoformat(data['timestamp'])
                    age = (datetime.now() - cached_time).seconds
                    info[name] = {
                        "exists": True,
                        "age_seconds": age,
                        "valid": age < self.cache_ttl.get(name, 3600),
                        "skill_count": len(data.get('skills', []))
                    }
                except Exception:
                    info[name] = {"exists": True, "error": True}
            else:
                info[name] = {"exists": False}
        
        return info


# 便捷函数
def get_skills_with_cache(force_refresh: bool = False) -> List[Dict]:
    """获取技能（带缓存）"""
    cache = SkillCacheManager()
    return cache.get_skills(force_refresh)


def get_popular_skills_with_cache(force_refresh: bool = False) -> List[Dict]:
    """获取热门技能（带缓存）"""
    cache = SkillCacheManager()
    return cache.get_popular_skills(force_refresh)
