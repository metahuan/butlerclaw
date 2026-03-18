# -*- coding: utf-8 -*-
"""
WebView 容器组件 - 用于嵌入复杂的 Web UI

支持:
- 图表展示 (ECharts, Chart.js)
- 富文本内容
- 第三方 Web 组件
- Python-JavaScript 双向通信
"""

import os
import json
import tempfile
from typing import Optional, Callable, Dict, Any
from pathlib import Path

try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as ttk
    from tkinter import ttk as ttk_module
    TTKBOOTSTRAP_AVAILABLE = False


class WebViewHost:
    """WebView 宿主类 - 管理 WebView 窗口和通信"""
    
    def __init__(self):
        self.window: Optional[webview.Window] = None
        self.callbacks: Dict[str, Callable] = {}
        self.html_content: str = ""
        self.temp_dir = tempfile.mkdtemp(prefix="butlerclaw_webview_")
    
    def create_window(self, title: str = "WebView", width: int = 800, height: int = 600):
        """创建 WebView 窗口"""
        if not WEBVIEW_AVAILABLE:
            raise ImportError("webview 模块未安装，请运行: pip install webview")
        
        self.window = webview.create_window(
            title=title,
            html=self.html_content,
            width=width,
            height=height
        )
        
        # 暴露 Python API 到 JavaScript
        self.window.expose(self._js_call_python)
        
        return self.window
    
    def _js_call_python(self, action: str, data: Any = None):
        """JavaScript 调用 Python"""
        if action in self.callbacks:
            return self.callbacks[action](data)
        return None
    
    def call_js(self, function_name: str, *args):
        """Python 调用 JavaScript"""
        if self.window:
            args_json = json.dumps(args)
            self.window.evaluate_js(f"{function_name}.apply(null, {args_json})")
    
    def register_callback(self, action: str, callback: Callable):
        """注册回调函数"""
        self.callbacks[action] = callback
    
    def set_html(self, html: str):
        """设置 HTML 内容"""
        self.html_content = html
        if self.window:
            self.window.load_html(html)
    
    def load_url(self, url: str):
        """加载 URL"""
        if self.window:
            self.window.load_url(url)
    
    def close(self):
        """关闭 WebView"""
        if self.window:
            self.window.destroy()
            self.window = None


class ChartWebView(ttk.Frame):
    """图表 WebView 组件 - 使用 ECharts 绘制图表"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.webview_host: Optional[WebViewHost] = None
        self.chart_data: Dict[str, Any] = {}
        
        # 创建容器
        self._build_ui()
    
    def _build_ui(self):
        """构建 UI"""
        # 如果 WebView 不可用，显示提示
        if not WEBVIEW_AVAILABLE:
            ttk.Label(self, text="WebView 未安装\n请运行: pip install webview",
                     justify=CENTER).pack(expand=True)
            return
        
        # 创建 WebView 容器
        # 注意：webview 需要独立的窗口，这里我们创建一个按钮来打开图表窗口
        ttk.Button(self, text="📊 打开图表视图",
                  command=self._open_chart_window).pack(expand=True)
    
    def _open_chart_window(self):
        """打开图表窗口"""
        self.webview_host = WebViewHost()
        
        # 生成 HTML 内容
        html = self._generate_chart_html()
        self.webview_host.set_html(html)
        
        # 注册回调
        self.webview_host.register_callback('chartClick', self._on_chart_click)
        
        # 创建窗口
        self.webview_host.create_window(
            title="成本分析图表",
            width=1000,
            height=700
        )
        
        # 启动 WebView (在单独线程中)
        import threading
        threading.Thread(target=webview.start, daemon=True).start()
    
    def _generate_chart_html(self) -> str:
        """生成图表 HTML"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>成本分析</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body { margin: 0; padding: 20px; font-family: system-ui, -apple-system, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; }
        .chart-container { height: 400px; margin-bottom: 20px; }
        h1 { color: #333; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 成本分析仪表板</h1>
        <div class="grid">
            <div id="trendChart" class="chart-container"></div>
            <div id="modelChart" class="chart-container"></div>
        </div>
        <div id="dailyChart" class="chart-container"></div>
    </div>
    
    <script>
        // 趋势图
        const trendChart = echarts.init(document.getElementById('trendChart'));
        trendChart.setOption({
            title: { text: '成本趋势', left: 'center' },
            tooltip: { trigger: 'axis' },
            xAxis: {
                type: 'category',
                data: ['1日', '5日', '10日', '15日', '20日', '25日', '30日']
            },
            yAxis: { type: 'value', name: '费用 (¥)' },
            series: [{
                name: '成本',
                type: 'line',
                smooth: true,
                data: [45, 52, 38, 65, 48, 72, 58],
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
                        ]
                    }
                },
                itemStyle: { color: '#3B82F6' }
            }]
        });
        
        // 模型对比图
        const modelChart = echarts.init(document.getElementById('modelChart'));
        modelChart.setOption({
            title: { text: '模型费用对比', left: 'center' },
            tooltip: { trigger: 'item' },
            legend: { bottom: '5%' },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: { show: false },
                emphasis: {
                    label: { show: true, fontSize: 16, fontWeight: 'bold' }
                },
                data: [
                    { value: 456, name: 'GPT-4o', itemStyle: { color: '#3B82F6' } },
                    { value: 321, name: 'Claude 3.5', itemStyle: { color: '#10B981' } },
                    { value: 123, name: 'DeepSeek', itemStyle: { color: '#F59E0B' } },
                    { value: 89, name: '其他', itemStyle: { color: '#6B7280' } }
                ]
            }]
        });
        
        // 每日费用图
        const dailyChart = echarts.init(document.getElementById('dailyChart'));
        dailyChart.setOption({
            title: { text: '每日费用明细', left: 'center' },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: { bottom: '5%' },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: Array.from({length: 30}, (_, i) => `${i+1}日`)
            },
            yAxis: { type: 'value', name: '费用 (¥)' },
            series: [
                {
                    name: '输入',
                    type: 'bar',
                    stack: 'total',
                    data: Array.from({length: 30}, () => Math.random() * 30 + 10),
                    itemStyle: { color: '#3B82F6' }
                },
                {
                    name: '输出',
                    type: 'bar',
                    stack: 'total',
                    data: Array.from({length: 30}, () => Math.random() * 50 + 20),
                    itemStyle: { color: '#10B981' }
                }
            ]
        });
        
        // 响应式
        window.addEventListener('resize', () => {
            trendChart.resize();
            modelChart.resize();
            dailyChart.resize();
        });
        
        // 点击事件
        trendChart.on('click', (params) => {
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.chartClick({ chart: 'trend', data: params });
            }
        });
    </script>
</body>
</html>
        '''
    
    def _on_chart_click(self, data):
        """图表点击事件"""
        print(f"图表点击: {data}")
        return {"status": "ok"}
    
    def update_data(self, data: Dict[str, Any]):
        """更新图表数据"""
        self.chart_data = data
        if self.webview_host:
            self.webview_host.call_js('updateChartData', data)
    
    def destroy(self):
        """销毁组件"""
        if self.webview_host:
            self.webview_host.close()
        super().destroy()


class SkillCardWebView(ttk.Frame):
    """技能卡片 WebView 组件"""
    
    def __init__(self, parent, skills: list = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.skills = skills or []
        self.webview_host: Optional[WebViewHost] = None
        
        self._build_ui()
    
    def _build_ui(self):
        """构建 UI"""
        if not WEBVIEW_AVAILABLE:
            ttk.Label(self, text="WebView 未安装",
                     justify=CENTER).pack(expand=True)
            return
        
        ttk.Button(self, text="🛠️ 浏览技能市场",
                  command=self._open_skills_window).pack(expand=True)
    
    def _open_skills_window(self):
        """打开技能市场窗口"""
        self.webview_host = WebViewHost()
        
        html = self._generate_skills_html()
        self.webview_host.set_html(html)
        
        self.webview_host.register_callback('installSkill', self._on_install_skill)
        self.webview_host.register_callback('viewSkillDetail', self._on_view_detail)
        
        self.webview_host.create_window(
            title="技能市场",
            width=1200,
            height=800
        )
        
        import threading
        threading.Thread(target=webview.start, daemon=True).start()
    
    def _generate_skills_html(self) -> str:
        """生成技能市场 HTML"""
        skills_html = ""
        for skill in self.skills:
            skills_html += f'''
            <div class="skill-card">
                <div class="skill-icon">{skill.get('icon', '📦')}</div>
                <div class="skill-info">
                    <h3>{skill.get('name', 'Unknown')}</h3>
                    <p>{skill.get('description', '')[:60]}...</p>
                    <div class="skill-meta">
                        <span>⭐ {skill.get('rating', 0)}</span>
                        <span>⬇ {skill.get('downloads', 0)}</span>
                    </div>
                </div>
                <button onclick="installSkill('{skill.get('id')}')">安装</button>
            </div>
            '''
        
        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>技能市场</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        
        .search-bar {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }}
        .search-bar input {{
            flex: 1;
            padding: 12px 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }}
        .search-bar button {{
            padding: 12px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
        }}
        
        .skills-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .skill-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .skill-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        .skill-icon {{
            font-size: 48px;
            margin-bottom: 15px;
        }}
        .skill-info h3 {{
            font-size: 18px;
            margin-bottom: 8px;
            color: #333;
        }}
        .skill-info p {{
            color: #666;
            font-size: 14px;
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .skill-meta {{
            display: flex;
            gap: 15px;
            color: #999;
            font-size: 13px;
        }}
        .skill-card button {{
            width: 100%;
            margin-top: 15px;
            padding: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        .skill-card button:hover {{
            background: #5568d3;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛠️ 技能市场</h1>
        <p>发现、安装、管理 OpenClaw 技能，让 AI 助手更强大</p>
    </div>
    
    <div class="search-bar">
        <input type="text" placeholder="搜索技能..." id="searchInput">
        <button onclick="searchSkills()">搜索</button>
    </div>
    
    <div class="skills-grid">
        {skills_html}
    </div>
    
    <script>
        function installSkill(skillId) {{
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.installSkill(skillId);
            }}
        }}
        
        function viewSkillDetail(skillId) {{
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.viewSkillDetail(skillId);
            }}
        }}
        
        function searchSkills() {{
            const query = document.getElementById('searchInput').value;
            console.log('搜索:', query);
        }}
    </script>
</body>
</html>
        '''
    
    def _on_install_skill(self, skill_id):
        """安装技能"""
        print(f"安装技能: {skill_id}")
        return {"status": "installing", "skill_id": skill_id}
    
    def _on_view_detail(self, skill_id):
        """查看技能详情"""
        print(f"查看技能详情: {skill_id}")
        return {"status": "ok"}
    
    def set_skills(self, skills: list):
        """设置技能列表"""
        self.skills = skills
        if self.webview_host:
            html = self._generate_skills_html()
            self.webview_host.set_html(html)
    
    def destroy(self):
        """销毁组件"""
        if self.webview_host:
            self.webview_host.close()
        super().destroy()


# 便捷函数
def create_chart_webview(parent, **kwargs) -> ChartWebView:
    """创建图表 WebView"""
    return ChartWebView(parent, **kwargs)


def create_skills_webview(parent, skills: list = None, **kwargs) -> SkillCardWebView:
    """创建技能卡片 WebView"""
    return SkillCardWebView(parent, skills, **kwargs)
