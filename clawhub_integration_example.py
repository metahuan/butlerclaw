#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClawHub API 集成示例

展示如何在 SkillsPanel 中集成 ClawHub API
"""

import tkinter as tk
from tkinter import ttk, messagebox


class ClawHubIntegrationExample:
    """ClawHub API 集成示例"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        # 热门推荐区域
        self._build_popular_section()
        
        # Trending 区域
        self._build_trending_section()
        
        # 新技能区域
        self._build_new_section()
        
        # 刷新按钮
        ttk.Button(
            self.parent, 
            text="刷新数据", 
            command=self._refresh_all
        ).pack(pady=10)
    
    def _build_popular_section(self):
        """构建热门推荐区域"""
        frame = ttk.LabelFrame(self.parent, text="🔥 热门技能", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.popular_container = ttk.Frame(frame)
        self.popular_container.pack(fill=tk.X)
        
        # 加载数据
        self._load_popular_skills()
    
    def _build_trending_section(self):
        """构建 Trending 区域"""
        frame = ttk.LabelFrame(self.parent, text="📈 Trending", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.trending_container = ttk.Frame(frame)
        self.trending_container.pack(fill=tk.X)
        
        # 加载数据
        self._load_trending_skills()
    
    def _build_new_section(self):
        """构建新技能区域"""
        frame = ttk.LabelFrame(self.parent, text="🆕 新技能", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.new_container = ttk.Frame(frame)
        self.new_container.pack(fill=tk.X)
        
        # 加载数据
        self._load_new_skills()
    
    def _load_popular_skills(self):
        """加载热门技能"""
        try:
            from skill_cache_manager import SkillCacheManager
            
            cache = SkillCacheManager()
            skills = cache.get_popular_skills()
            
            # 清空容器
            for widget in self.popular_container.winfo_children():
                widget.destroy()
            
            if not skills:
                ttk.Label(
                    self.popular_container, 
                    text="暂无数据", 
                    foreground="gray"
                ).pack(pady=10)
                return
            
            # 显示技能卡片（横向排列）
            for skill in skills[:5]:  # 只显示前5个
                self._create_skill_card(
                    self.popular_container, 
                    skill,
                    side=tk.LEFT
                )
                
        except Exception as e:
            ttk.Label(
                self.popular_container, 
                text=f"加载失败: {e}", 
                foreground="red"
            ).pack(pady=10)
    
    def _load_trending_skills(self):
        """加载 trending 技能"""
        try:
            from skill_cache_manager import SkillCacheManager
            
            cache = SkillCacheManager()
            skills = cache.get_trending_skills()
            
            for widget in self.trending_container.winfo_children():
                widget.destroy()
            
            if not skills:
                ttk.Label(
                    self.trending_container, 
                    text="暂无数据", 
                    foreground="gray"
                ).pack(pady=10)
                return
            
            for skill in skills[:3]:
                self._create_skill_list_item(self.trending_container, skill)
                
        except Exception as e:
            ttk.Label(
                self.trending_container, 
                text=f"加载失败: {e}", 
                foreground="red"
            ).pack(pady=10)
    
    def _load_new_skills(self):
        """加载新技能"""
        try:
            from skill_cache_manager import SkillCacheManager
            
            cache = SkillCacheManager()
            skills = cache.get_new_skills()
            
            for widget in self.new_container.winfo_children():
                widget.destroy()
            
            if not skills:
                ttk.Label(
                    self.new_container, 
                    text="暂无数据", 
                    foreground="gray"
                ).pack(pady=10)
                return
            
            for skill in skills[:3]:
                self._create_skill_list_item(self.new_container, skill)
                
        except Exception as e:
            ttk.Label(
                self.new_container, 
                text=f"加载失败: {e}", 
                foreground="red"
            ).pack(pady=10)
    
    def _create_skill_card(self, parent, skill: dict, side=tk.TOP):
        """创建技能卡片"""
        card = ttk.Frame(parent, relief="solid", padding=10)
        card.pack(side=side, padx=5, pady=5)
        
        # 图标
        icon = skill.get('icon', '📦')
        ttk.Label(card, text=icon, font=("", 24)).pack()
        
        # 名称
        name = skill.get('name', 'Unknown')
        ttk.Label(
            card, 
            text=name, 
            font=("Microsoft YaHei", 10, "bold"),
            wraplength=100
        ).pack()
        
        # 下载量和评分
        meta = skill.get('meta', {})
        downloads = meta.get('downloads', '0')
        rating = meta.get('rating', '0')
        
        info_text = f"⬇ {downloads}  ⭐ {rating}"
        ttk.Label(
            card, 
            text=info_text, 
            font=("", 8),
            foreground="gray"
        ).pack()
        
        # 安装按钮
        ttk.Button(
            card, 
            text="安装", 
            width=8,
            command=lambda s=skill: self._install_skill(s)
        ).pack(pady=5)
    
    def _create_skill_list_item(self, parent, skill: dict):
        """创建技能列表项"""
        item = ttk.Frame(parent)
        item.pack(fill=tk.X, pady=2)
        
        # 图标
        icon = skill.get('icon', '📦')
        ttk.Label(item, text=icon, font=("", 16)).pack(side=tk.LEFT, padx=5)
        
        # 信息
        info_frame = ttk.Frame(item)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name = skill.get('name', 'Unknown')
        ttk.Label(
            info_frame, 
            text=name, 
            font=("Microsoft YaHei", 10, "bold")
        ).pack(anchor=tk.W)
        
        # 元信息
        meta = skill.get('meta', {})
        author = meta.get('author', 'Unknown')
        updated = skill.get('updated_at', '')
        
        meta_text = f"👤 {author}  📅 {updated}"
        ttk.Label(
            info_frame, 
            text=meta_text, 
            font=("", 8),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # 安装按钮
        ttk.Button(
            item, 
            text="安装", 
            width=8,
            command=lambda s=skill: self._install_skill(s)
        ).pack(side=tk.RIGHT, padx=5)
    
    def _install_skill(self, skill: dict):
        """安装技能"""
        skill_id = skill.get('id')
        skill_name = skill.get('name', skill_id)
        
        messagebox.showinfo(
            "安装技能",
            f"开始安装: {skill_name}\n\n"
            f"技能ID: {skill_id}\n\n"
            f"（实际实现时会调用安装队列）"
        )
    
    def _refresh_all(self):
        """刷新所有数据"""
        self._load_popular_skills()
        self._load_trending_skills()
        self._load_new_skills()
        messagebox.showinfo("刷新", "数据已刷新")


# 演示代码
if __name__ == "__main__":
    root = tk.Tk()
    root.title("ClawHub API 集成示例")
    root.geometry("800x600")
    
    # 创建示例
    example = ClawHubIntegrationExample(root)
    
    root.mainloop()
