"""
实时漏洞监控系统

提供持续的漏洞监控和预警功能：
- CVE 数据库实时同步
- 依赖包漏洞监控
- 安全公告订阅
- 漏洞预警通知
- 修复建议自动生成
"""

import os
import json
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import urllib.request
import urllib.error


class MonitorStatus(Enum):
    """监控状态"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class VulnerabilityAlert:
    """漏洞告警"""
    id: str
    cve_id: Optional[str]
    title: str
    severity: str
    affected_packages: List[str]
    description: str
    published_date: str
    detected_at: str
    acknowledged: bool = False
    fixed: bool = False


@dataclass
class MonitoredPackage:
    """被监控的包"""
    name: str
    current_version: str
    ecosystem: str  # pip, npm, etc.
    last_check: Optional[str] = None
    known_vulnerabilities: List[str] = None
    
    def __post_init__(self):
        if self.known_vulnerabilities is None:
            self.known_vulnerabilities = []


class RealtimeVulnMonitor:
    """
    实时漏洞监控系统
    
    功能：
    1. 定时同步 CVE 数据库
    2. 监控已安装包的漏洞
    3. 订阅安全公告
    4. 漏洞预警通知
    5. 生成修复建议
    """
    
    CONFIG_DIR = os.path.expanduser("~/.openclaw/security")
    MONITOR_DB_PATH = os.path.join(CONFIG_DIR, "vuln_monitor.json")
    ALERTS_PATH = os.path.join(CONFIG_DIR, "vuln_alerts.json")
    
    # 监控源
    SOURCES = {
        "github_advisory": "https://api.github.com/advisories",
        "cve_feed": "https://cve.mitre.org/data/downloads/allitems.xml",
        "npm_audit": "https://registry.npmjs.org/-/npm/v1/security/advisories",
        "pypi_audit": "https://pypi.org/pypi/{package}/json",
    }
    
    # 默认监控间隔（分钟）
    DEFAULT_INTERVAL = 60
    
    def __init__(self):
        self._status = MonitorStatus.STOPPED
        self._monitored_packages: Dict[str, MonitoredPackage] = {}
        self._alerts: List[VulnerabilityAlert] = []
        self._callbacks: List[Callable] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._ensure_db_dir()
        self._load_data()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def _load_data(self):
        """加载监控数据"""
        # 加载监控包列表
        if os.path.exists(self.MONITOR_DB_PATH):
            try:
                with open(self.MONITOR_DB_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pkg_data in data.get("packages", []):
                        pkg = MonitoredPackage(**pkg_data)
                        self._monitored_packages[pkg.name] = pkg
            except Exception:
                pass
        
        # 加载告警历史
        if os.path.exists(self.ALERTS_PATH):
            try:
                with open(self.ALERTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for alert_data in data.get("alerts", []):
                        self._alerts.append(VulnerabilityAlert(**alert_data))
            except Exception:
                pass
    
    def _save_data(self):
        """保存监控数据"""
        # 保存监控包列表
        monitor_data = {
            "updated_at": datetime.now().isoformat(),
            "packages": [
                asdict(pkg) for pkg in self._monitored_packages.values()
            ],
        }
        with open(self.MONITOR_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(monitor_data, f, ensure_ascii=False, indent=2)
        
        # 保存告警（只保留最近 500 条）
        alerts_data = {
            "updated_at": datetime.now().isoformat(),
            "alerts": [asdict(a) for a in self._alerts[-500:]],
        }
        with open(self.ALERTS_PATH, "w", encoding="utf-8") as f:
            json.dump(alerts_data, f, ensure_ascii=False, indent=2)
    
    # --- 包监控管理 ---
    
    def add_package(
        self,
        name: str,
        version: str,
        ecosystem: str = "pip",
    ) -> Dict[str, Any]:
        """
        添加监控包
        
        Args:
            name: 包名
            version: 当前版本
            ecosystem: 生态系统 (pip, npm)
            
        Returns:
            添加结果
        """
        pkg = MonitoredPackage(
            name=name,
            current_version=version,
            ecosystem=ecosystem,
        )
        self._monitored_packages[name] = pkg
        self._save_data()
        
        # 立即检查一次
        self._check_package(pkg)
        
        return {
            "success": True,
            "message": f"已添加 {name}@{version} 到监控列表",
        }
    
    def remove_package(self, name: str) -> Dict[str, Any]:
        """移除监控包"""
        if name not in self._monitored_packages:
            return {
                "success": False,
                "message": f"{name} 不在监控列表中",
            }
        
        del self._monitored_packages[name]
        self._save_data()
        
        return {
            "success": True,
            "message": f"已移除 {name} 的监控",
        }
    
    def list_monitored_packages(self) -> List[MonitoredPackage]:
        """列出所有监控的包"""
        return list(self._monitored_packages.values())
    
    def scan_installed_packages(self) -> Dict[str, Any]:
        """
        扫描已安装的包并添加到监控
        
        自动检测 requirements.txt 和 package.json
        """
        added = []
        
        # 扫描 Python 包
        pip_packages = self._detect_pip_packages()
        for name, version in pip_packages.items():
            if name not in self._monitored_packages:
                self.add_package(name, version, "pip")
                added.append(f"{name}@{version}")
        
        # 扫描 Node.js 包
        npm_packages = self._detect_npm_packages()
        for name, version in npm_packages.items():
            if name not in self._monitored_packages:
                self.add_package(name, version, "npm")
                added.append(f"{name}@{version}")
        
        return {
            "success": True,
            "added": added,
            "total_monitored": len(self._monitored_packages),
        }
    
    def _detect_pip_packages(self) -> Dict[str, str]:
        """检测已安装的 Python 包"""
        packages = {}
        
        # 尝试读取 requirements.txt
        req_file = "requirements.txt"
        if os.path.exists(req_file):
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "==" in line:
                            name, version = line.split("==", 1)
                            packages[name.strip()] = version.strip()
            except Exception:
                pass
        
        # 尝试使用 pip list
        try:
            import subprocess
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                pip_list = json.loads(result.stdout)
                for pkg in pip_list:
                    packages[pkg["name"]] = pkg["version"]
        except Exception:
            pass
        
        return packages
    
    def _detect_npm_packages(self) -> Dict[str, str]:
        """检测已安装的 Node.js 包"""
        packages = {}
        
        # 尝试读取 package.json
        pkg_file = "package.json"
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    
                    for name, version in {**deps, **dev_deps}.items():
                        # 移除版本号前缀
                        clean_version = version.lstrip("^~>=<")
                        packages[name] = clean_version
            except Exception:
                pass
        
        return packages
    
    # --- 监控执行 ---
    
    def start_monitoring(self, interval_minutes: int = None):
        """
        启动监控
        
        Args:
            interval_minutes: 检查间隔（分钟）
        """
        if self._status == MonitorStatus.RUNNING:
            return {"success": False, "message": "监控已在运行中"}
        
        interval = interval_minutes or self.DEFAULT_INTERVAL
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
        )
        self._monitor_thread.start()
        self._status = MonitorStatus.RUNNING
        
        return {
            "success": True,
            "message": f"监控已启动，检查间隔: {interval} 分钟",
        }
    
    def stop_monitoring(self):
        """停止监控"""
        if self._status != MonitorStatus.RUNNING:
            return {"success": False, "message": "监控未在运行"}
        
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self._status = MonitorStatus.STOPPED
        return {"success": True, "message": "监控已停止"}
    
    def pause_monitoring(self):
        """暂停监控"""
        if self._status == MonitorStatus.RUNNING:
            self._status = MonitorStatus.PAUSED
            return {"success": True, "message": "监控已暂停"}
        return {"success": False, "message": "监控未在运行"}
    
    def resume_monitoring(self):
        """恢复监控"""
        if self._status == MonitorStatus.PAUSED:
            self._status = MonitorStatus.RUNNING
            return {"success": True, "message": "监控已恢复"}
        return {"success": False, "message": "监控未在暂停状态"}
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            "status": self._status.value,
            "monitored_packages": len(self._monitored_packages),
            "total_alerts": len(self._alerts),
            "unacknowledged_alerts": len([a for a in self._alerts if not a.acknowledged]),
        }
    
    def _monitor_loop(self, interval_minutes: int):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                if self._status == MonitorStatus.RUNNING:
                    self._run_check()
                
                # 等待下一次检查
                for _ in range(interval_minutes * 60):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self._status = MonitorStatus.ERROR
                print(f"监控循环错误: {e}")
                time.sleep(60)  # 出错后等待 1 分钟再试
    
    def _run_check(self):
        """执行一次检查"""
        print(f"[{datetime.now()}] 执行漏洞检查...")
        
        for pkg in self._monitored_packages.values():
            try:
                self._check_package(pkg)
            except Exception as e:
                print(f"检查 {pkg.name} 失败: {e}")
        
        # 同步 CVE 数据库
        try:
            self._sync_cve_database()
        except Exception as e:
            print(f"同步 CVE 数据库失败: {e}")
    
    def _check_package(self, pkg: MonitoredPackage):
        """检查单个包的漏洞"""
        # 使用漏洞数据库检查
        try:
            from .vulnerability_db import VulnerabilityDatabase
            vuln_db = VulnerabilityDatabase()
            
            hits = vuln_db.check_package_vulnerable(pkg.name, pkg.current_version)
            
            for hit in hits:
                if hit.id not in pkg.known_vulnerabilities:
                    # 新发现的漏洞
                    alert = VulnerabilityAlert(
                        id=f"ALERT-{hit.id}",
                        cve_id=hit.id,
                        title=hit.name,
                        severity=hit.severity,
                        affected_packages=[pkg.name],
                        description=hit.description,
                        published_date=datetime.now().isoformat(),
                        detected_at=datetime.now().isoformat(),
                    )
                    self._alerts.append(alert)
                    pkg.known_vulnerabilities.append(hit.id)
                    
                    # 触发回调
                    self._notify_callbacks(alert, pkg)
            
            pkg.last_check = datetime.now().isoformat()
            self._save_data()
            
        except Exception as e:
            print(f"漏洞检查失败: {e}")
    
    def _sync_cve_database(self):
        """同步 CVE 数据库"""
        try:
            from .vulnerability_db import VulnerabilityDatabase
            vuln_db = VulnerabilityDatabase()
            result = vuln_db.update_database()
            
            if result["success"]:
                print(f"CVE 数据库同步完成: {result.get('message', '')}")
            
        except Exception as e:
            print(f"CVE 同步失败: {e}")
    
    # --- 告警管理 ---
    
    def get_alerts(
        self,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[VulnerabilityAlert]:
        """获取漏洞告警"""
        alerts = self._alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        # 按时间倒序
        alerts = sorted(alerts, key=lambda a: a.detected_at, reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._save_data()
                return True
        return False
    
    def mark_alert_fixed(self, alert_id: str) -> bool:
        """标记告警为已修复"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.fixed = True
                self._save_data()
                return True
        return False
    
    def register_callback(self, callback: Callable):
        """注册漏洞发现回调"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, alert: VulnerabilityAlert, pkg: MonitoredPackage):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(alert, pkg)
            except Exception as e:
                print(f"回调执行失败: {e}")
    
    # --- 修复建议 ---
    
    def generate_fix_plan(self, alert_id: str) -> Dict[str, Any]:
        """
        生成修复计划
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            修复计划
        """
        alert = next((a for a in self._alerts if a.id == alert_id), None)
        if not alert:
            return {"success": False, "message": "告警不存在"}
        
        # 查找受影响的包
        affected = []
        for pkg_name in alert.affected_packages:
            pkg = self._monitored_packages.get(pkg_name)
            if pkg:
                affected.append(pkg)
        
        # 生成修复步骤
        steps = []
        for pkg in affected:
            if pkg.ecosystem == "pip":
                steps.append({
                    "package": pkg.name,
                    "current_version": pkg.current_version,
                    "action": "upgrade",
                    "command": f"pip install --upgrade {pkg.name}",
                })
            elif pkg.ecosystem == "npm":
                steps.append({
                    "package": pkg.name,
                    "current_version": pkg.current_version,
                    "action": "upgrade",
                    "command": f"npm update {pkg.name}",
                })
        
        return {
            "success": True,
            "alert_id": alert_id,
            "title": alert.title,
            "severity": alert.severity,
            "steps": steps,
            "estimated_time": f"{len(steps) * 2} 分钟",
        }
    
    def generate_security_report(self) -> Dict[str, Any]:
        """生成安全报告"""
        total_alerts = len(self._alerts)
        unacknowledged = len([a for a in self._alerts if not a.acknowledged])
        unfixed = len([a for a in self._alerts if not a.fixed])
        
        # 按严重等级统计
        severity_counts = {}
        for alert in self._alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        
        # 最近 7 天的新告警
        week_ago = datetime.now() - timedelta(days=7)
        recent_alerts = [
            a for a in self._alerts
            if datetime.fromisoformat(a.detected_at) >= week_ago
        ]
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_alerts": total_alerts,
                "unacknowledged": unacknowledged,
                "unfixed": unfixed,
                "monitored_packages": len(self._monitored_packages),
            },
            "severity_distribution": severity_counts,
            "recent_alerts_7d": len(recent_alerts),
            "high_priority": [
                {
                    "id": a.id,
                    "title": a.title,
                    "severity": a.severity,
                    "detected_at": a.detected_at,
                }
                for a in self._alerts
                if a.severity in ("CRITICAL", "HIGH") and not a.fixed
            ][:10],
        }


# --- 便捷函数 ---

def start_vuln_monitoring(interval_minutes: int = 60) -> Dict[str, Any]:
    """便捷函数：启动漏洞监控"""
    monitor = RealtimeVulnMonitor()
    
    # 自动扫描已安装包
    monitor.scan_installed_packages()
    
    # 启动监控
    return monitor.start_monitoring(interval_minutes)


def check_vulnerabilities() -> List[VulnerabilityAlert]:
    """便捷函数：检查漏洞告警"""
    monitor = RealtimeVulnMonitor()
    return monitor.get_alerts(acknowledged=False)


def get_vuln_report() -> Dict[str, Any]:
    """便捷函数：获取漏洞报告"""
    monitor = RealtimeVulnMonitor()
    return monitor.generate_security_report()
