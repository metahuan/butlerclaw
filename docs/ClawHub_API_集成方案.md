# ClawHub API 集成方案

## 概述

本文档介绍如何将 ClawHub (clawhub.ai) 的技能数据集成到 OpenClaw Butler 中。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     SkillsPanel (UI)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 热门推荐    │  │ Trending    │  │ 新技能      │         │
│  │ (Popular)   │  │             │  │ (New)       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                 SkillCacheManager                           │
│         (本地缓存 + 离线支持 + 缓存策略)                      │
├─────────────────────────────────────────────────────────────┤
│                    ClawHubAPI                               │
│              (API 客户端 + 数据模型)                         │
├─────────────────────────────────────────────────────────────┤
│              ClawHub Server / 模拟数据                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. ClawHubAPI - API 客户端

**文件**: `clawhub_api.py`

**功能**:
- 获取热门技能
- 搜索技能
- 获取技能详情
- 获取 trending 技能
- 获取新技能

**使用示例**:
```python
from clawhub_api import ClawHubAPI

api = ClawHubAPI()

# 获取热门技能
skills = api.get_popular_skills(limit=20)

# 搜索技能
results = api.search_skills("browser", limit=10)

# 获取技能详情
detail = api.get_skill_details("skill-vetter")
```

**数据模型**:
```python
@dataclass
class ClawHubSkill:
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
```

---

### 2. SkillCacheManager - 缓存管理器

**文件**: `skill_cache_manager.py`

**功能**:
- 本地缓存技能数据
- 支持离线使用
- 自动缓存过期策略
- 缓存信息查询

**缓存策略**:
| 数据类型 | 缓存时间 | 说明 |
|---------|---------|------|
| 全部技能 | 1小时 | 基础数据，更新频率低 |
| 热门技能 | 30分钟 | 相对稳定 |
| Trending | 10分钟 | 变化较快 |
| 新技能 | 30分钟 | 定期更新 |

**使用示例**:
```python
from skill_cache_manager import SkillCacheManager

cache = SkillCacheManager()

# 获取技能（自动使用缓存）
skills = cache.get_skills()

# 强制刷新
skills = cache.get_skills(force_refresh=True)

# 搜索技能（优先本地缓存）
results = cache.search_skills("browser")

# 获取缓存信息
info = cache.get_cache_info()
print(info)
# {
#   "skills": {"exists": True, "age_seconds": 1800, "valid": True, "skill_count": 50},
#   "popular": {"exists": True, "age_seconds": 600, "valid": True, "skill_count": 20},
#   ...
# }
```

---

## API 端点说明

### 当前实现

当前使用的是**模拟数据**，实际部署时需要替换为真实的 ClawHub API。

### 预期的真实 API 端点

```
# 基础URL
BASE_URL = "https://api.clawhub.ai/v1"

# 获取热门技能
GET /skills/popular?limit={limit}

# 搜索技能
GET /skills/search?q={query}&limit={limit}

# 获取技能详情
GET /skills/{skill_id}

# 获取 trending 技能
GET /skills/trending?limit={limit}

# 获取新技能
GET /skills/new?limit={limit}

# 按分类获取技能
GET /skills?category={category}&limit={limit}

# 获取技能 README
GET /skills/{skill_id}/readme
```

### 认证方式

```python
# 方式1: API Key
api = ClawHubAPI(api_key="your-api-key")

# 方式2: 无需认证（公开API）
api = ClawHubAPI()
```

---

## 集成到 SkillsPanel

### 步骤1: 修改 SkillsManager

在 `skills_manager.py` 中集成 ClawHub 数据：

```python
class SkillManager:
    def __init__(self):
        self.cache_manager = SkillCacheManager()
        self.bundled_skills = BUNDLED_SKILLS  # 内置技能
    
    def get_skills(self, force_refresh=False):
        """获取所有技能（内置 + ClawHub）"""
        skills = []
        
        # 1. 内置技能（离线可用）
        skills.extend(self.bundled_skills)
        
        # 2. ClawHub 技能（带缓存）
        try:
            clawhub_skills = self.cache_manager.get_skills(force_refresh)
            skills.extend(clawhub_skills)
        except Exception as e:
            print(f"获取 ClawHub 技能失败: {e}")
        
        # 3. 已安装技能
        installed = self._get_installed_skills()
        
        # 合并和去重
        return self._merge_skills(skills, installed)
    
    def get_popular_skills(self):
        """获取热门技能"""
        return self.cache_manager.get_popular_skills()
    
    def get_trending_skills(self):
        """获取 trending 技能"""
        return self.cache_manager.get_trending_skills()
    
    def get_new_skills(self):
        """获取新技能"""
        return self.cache_manager.get_new_skills()
```

### 步骤2: 修改 SkillsPanel UI

在 `openclaw_assistant.py` 的 `SkillsPanel` 中添加推荐区域：

```python
class SkillsPanel(BasePanel):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)
        
        # ... 现有代码 ...
        
        # 添加 ClawHub 推荐区域
        self._build_recommendation_sections()
    
    def _build_recommendation_sections(self):
        """构建推荐区域"""
        # 热门推荐
        self.popular_frame = ttk.LabelFrame(self, text="🔥 热门技能", padding=10)
        self.popular_frame.pack(fill=tk.X, pady=5)
        self._load_popular_skills()
        
        # Trending
        self.trending_frame = ttk.LabelFrame(self, text="📈 Trending", padding=10)
        self.trending_frame.pack(fill=tk.X, pady=5)
        self._load_trending_skills()
        
        # 新技能
        self.new_frame = ttk.LabelFrame(self, text="🆕 新技能", padding=10)
        self.new_frame.pack(fill=tk.X, pady=5)
        self._load_new_skills()
    
    def _load_popular_skills(self):
        """加载热门技能"""
        skills = self.manager.get_popular_skills()
        # 显示技能卡片...
    
    def _load_trending_skills(self):
        """加载 trending 技能"""
        skills = self.manager.get_trending_skills()
        # 显示技能列表...
    
    def _load_new_skills(self):
        """加载新技能"""
        skills = self.manager.get_new_skills()
        # 显示技能列表...
```

---

## 离线支持

### 缓存文件位置

```
~/.openclaw/cache/
├── skills_cache.json      # 全部技能
├── popular_cache.json     # 热门技能
├── trending_cache.json    # Trending
└── new_cache.json         # 新技能
```

### 离线模式行为

1. **有缓存**: 直接使用缓存数据
2. **缓存过期**: 尝试更新，失败则使用过期缓存
3. **无缓存**: 显示内置技能 + 提示用户联网

---

## 实施步骤

### 阶段1: 基础集成（1-2天）

1. ✅ 创建 `clawhub_api.py` - API 客户端
2. ✅ 创建 `skill_cache_manager.py` - 缓存管理器
3. ⬜ 修改 `skills_manager.py` - 集成数据源
4. ⬜ 测试数据获取和缓存

### 阶段2: UI集成（2-3天）

1. ⬜ 修改 `SkillsPanel` - 添加推荐区域
2. ⬜ 创建技能卡片组件
3. ⬜ 实现数据加载和显示
4. ⬜ 添加刷新按钮

### 阶段3: 优化完善（1-2天）

1. ⬜ 错误处理和重试机制
2. ⬜ 加载状态显示
3. ⬜ 离线提示
4. ⬜ 性能优化

---

## 注意事项

### 1. API 限制

- 注意 API 调用频率限制
- 实现请求队列和重试机制
- 使用缓存减少 API 调用

### 2. 网络异常处理

```python
try:
    skills = api.get_popular_skills()
except NetworkError:
    # 使用缓存数据
    skills = cache.get_skills()
    messagebox.showwarning("网络错误", "使用离线缓存数据")
```

### 3. 数据一致性

- 内置技能优先（确保离线可用）
- ClawHub 数据作为补充
- 合并时去重（以 skill_id 为准）

---

## 测试

### 单元测试

```python
def test_clawhub_api():
    api = ClawHubAPI()
    skills = api.get_popular_skills(limit=5)
    assert len(skills) == 5
    assert all(hasattr(s, 'id') for s in skills)

def test_skill_cache():
    cache = SkillCacheManager()
    
    # 测试缓存写入
    cache._write_cache(cache.skills_cache_file, [{'id': 'test'}])
    
    # 测试缓存读取
    skills = cache._read_cache(cache.skills_cache_file)
    assert len(skills) == 1
```

### 集成测试

```python
def test_skills_panel_integration():
    # 测试 SkillsPanel 是否能正确显示 ClawHub 数据
    pass
```

---

## 后续优化

1. **个性化推荐** - 基于用户已安装技能推荐
2. **技能评分** - 允许用户对技能评分
3. **评论系统** - 查看其他用户的评论
4. **版本检查** - 检查已安装技能是否有更新
5. **依赖图谱** - 显示技能之间的依赖关系

---

## 相关文件

- `clawhub_api.py` - API 客户端
- `skill_cache_manager.py` - 缓存管理器
- `clawhub_integration_example.py` - 集成示例
- `skills_manager.py` - 需要修改
- `openclaw_assistant.py` - 需要修改

---

## 参考

- ClawHub 网站: https://clawhub.ai
- OpenClaw 文档: https://docs.openclaw.ai
