"""
技能安全扫描器 - 深度静态代码分析版

提供全面的技能代码安全检查：
- 危险函数检测 (eval, exec, os.system 等)
- 网络调用分析
- 文件系统操作分析
- 敏感权限检查
- 依赖包安全检查
- 代码签名验证
"""

import os
import re
import ast
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .models import SkillSecurityReport


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


@dataclass
class CodeIssue:
    """代码问题"""
    severity: RiskLevel
    category: str
    message: str
    file: str
    line: int
    code: str
    fix_suggestion: str


@dataclass
class NetworkCall:
    """网络调用"""
    url: str
    method: str
    is_external: bool
    is_encrypted: bool
    line: int


@dataclass
class FileOperation:
    """文件操作"""
    path: str
    operation: str  # read, write, delete, execute
    is_sensitive: bool
    line: int


@dataclass
class PermissionUsage:
    """权限使用"""
    permission: str
    description: str
    risk_level: RiskLevel
    line: int


class SkillSecurityScanner:
    """
    技能安全扫描器 - 深度静态分析
    
    分析维度：
    1. 危险函数调用
    2. 网络请求
    3. 文件系统操作
    4. 敏感权限
    5. 依赖包安全
    6. 代码签名
    """
    
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        # 代码执行
        "eval": {"severity": RiskLevel.CRITICAL, "desc": "执行任意代码表达式"},
        "exec": {"severity": RiskLevel.CRITICAL, "desc": "执行任意代码"},
        "compile": {"severity": RiskLevel.HIGH, "desc": "编译代码（可能被滥用）"},
        "__import__": {"severity": RiskLevel.HIGH, "desc": "动态导入模块"},
        
        # 系统命令
        "os.system": {"severity": RiskLevel.CRITICAL, "desc": "执行系统命令"},
        "os.popen": {"severity": RiskLevel.CRITICAL, "desc": "执行系统命令并读取输出"},
        "subprocess.call": {"severity": RiskLevel.CRITICAL, "desc": "执行子进程"},
        "subprocess.run": {"severity": RiskLevel.CRITICAL, "desc": "执行子进程"},
        "subprocess.Popen": {"severity": RiskLevel.CRITICAL, "desc": "执行子进程"},
        "subprocess.check_output": {"severity": RiskLevel.CRITICAL, "desc": "执行子进程并获取输出"},
        
        # 文件操作
        "os.remove": {"severity": RiskLevel.MEDIUM, "desc": "删除文件"},
        "os.rmdir": {"severity": RiskLevel.MEDIUM, "desc": "删除目录"},
        "os.unlink": {"severity": RiskLevel.MEDIUM, "desc": "删除文件"},
        "shutil.rmtree": {"severity": RiskLevel.HIGH, "desc": "递归删除目录"},
        
        # 网络
        "socket.socket": {"severity": RiskLevel.MEDIUM, "desc": "创建网络套接字"},
        
        # 反序列化
        "pickle.loads": {"severity": RiskLevel.CRITICAL, "desc": "反序列化（可能被利用执行代码）"},
        "yaml.load": {"severity": RiskLevel.HIGH, "desc": "YAML 反序列化（使用 unsafe loader）"},
        "marshal.loads": {"severity": RiskLevel.CRITICAL, "desc": "反序列化"},
        
        # 反射/内省
        "getattr": {"severity": RiskLevel.LOW, "desc": "动态获取属性"},
        "setattr": {"severity": RiskLevel.MEDIUM, "desc": "动态设置属性"},
        "globals": {"severity": RiskLevel.LOW, "desc": "获取全局变量"},
        "locals": {"severity": RiskLevel.LOW, "desc": "获取局部变量"},
    }
    
    # 敏感文件路径模式
    SENSITIVE_PATHS = [
        r".*\.openclaw.*",
        r".*\.ssh.*",
        r".*\.aws.*",
        r".*\.docker.*",
        r".*/etc/passwd.*",
        r".*/etc/shadow.*",
        r".*id_rsa.*",
        r".*id_dsa.*",
        r".*\.env.*",
        r".*config.*\.json",
        r".*secret.*",
        r".*credential.*",
        r".*token.*",
        r".*password.*",
        r".*apikey.*",
        r".*api_key.*",
    ]
    
    # 网络请求库
    NETWORK_LIBS = {
        "requests": ["get", "post", "put", "delete", "patch", "head", "options"],
        "urllib.request": ["urlopen", "Request"],
        "http.client": ["HTTPConnection", "HTTPSConnection"],
        "httpx": ["get", "post", "put", "delete", "patch", "head", "options"],
        "aiohttp": ["ClientSession", "get", "post"],
    }
    
    # 文件操作函数
    FILE_OPERATIONS = {
        "open": ["read", "write", "readline", "readlines", "write", "writelines"],
        "os.open": ["read", "write"],
        "pathlib.Path": ["read_text", "read_bytes", "write_text", "write_bytes"],
    }
    
    def __init__(self, skills_root: str | None = None, vuln_db=None) -> None:
        self.skills_root = skills_root or os.path.expanduser("~/.openclaw/skills")
        self.vuln_db = vuln_db  # 漏洞数据库引用
        self._issues: List[CodeIssue] = []
        self._network_calls: List[NetworkCall] = []
        self._file_operations: List[FileOperation] = []
        self._permissions: List[PermissionUsage] = []
    
    def scan_all(self) -> List[SkillSecurityReport]:
        """
        扫描所有已安装技能
        
        Returns:
            技能安全报告列表
        """
        if not os.path.isdir(self.skills_root):
            return []
        
        reports: List[SkillSecurityReport] = []
        
        for skill_name in sorted(os.listdir(self.skills_root)):
            skill_path = os.path.join(self.skills_root, skill_name)
            if not os.path.isdir(skill_path):
                continue
            
            report = self.scan_skill(skill_name, skill_path)
            reports.append(report)
        
        return reports
    
    def scan_skill(self, skill_name: str, skill_path: str) -> SkillSecurityReport:
        """
        扫描单个技能
        
        Args:
            skill_name: 技能名称
            skill_path: 技能目录路径
            
        Returns:
            技能安全报告
        """
        # 重置状态
        self._issues = []
        self._network_calls = []
        self._file_operations = []
        self._permissions = []
        
        # 收集所有 Python 文件
        py_files = self._collect_python_files(skill_path)
        
        # 分析每个文件
        for file_path in py_files:
            self._analyze_file(file_path)
        
        # 检查依赖安全
        self._check_dependencies(skill_path)
        
        # 检查代码签名
        signature_valid = self._verify_signature(skill_path)
        
        # 推断信任级别
        trust_level = self._calculate_trust_level(skill_name, len(self._issues))
        
        # 判断是否有可疑行为
        is_suspicious = any(
            issue.severity in (RiskLevel.CRITICAL, RiskLevel.HIGH)
            for issue in self._issues
        )
        
        # 生成权限摘要
        permissions_summary = self._generate_permissions_summary()
        
        # 生成网络调用摘要
        network_summary = self._generate_network_summary()
        
        # 生成文件操作摘要
        file_summary = self._generate_file_summary()
        
        return SkillSecurityReport(
            id=skill_name,
            name=skill_name,
            trust_level=trust_level,
            is_suspicious=is_suspicious,
            permissions=permissions_summary,
            network_calls=network_summary,
            file_operations=file_summary,
            issues_count=len(self._issues),
            critical_count=len([i for i in self._issues if i.severity == RiskLevel.CRITICAL]),
            high_count=len([i for i in self._issues if i.severity == RiskLevel.HIGH]),
            medium_count=len([i for i in self._issues if i.severity == RiskLevel.MEDIUM]),
            signature_valid=signature_valid,
            details=self._generate_details(),
        )
    
    def _collect_python_files(self, skill_path: str) -> List[str]:
        """收集技能目录下的所有 Python 文件"""
        py_files = []
        for root, _, files in os.walk(skill_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
        return py_files
    
    def _analyze_file(self, file_path: str) -> None:
        """分析单个 Python 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return
        
        # 解析 AST
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return
        
        # 分析 AST
        analyzer = ASTSecurityAnalyzer(
            file_path=file_path,
            source=source,
            dangerous_functions=self.DANGEROUS_FUNCTIONS,
            network_libs=self.NETWORK_LIBS,
            file_operations=self.FILE_OPERATIONS,
        )
        analyzer.visit(tree)
        
        # 收集结果
        self._issues.extend(analyzer.issues)
        self._network_calls.extend(analyzer.network_calls)
        self._file_operations.extend(analyzer.file_operations)
        self._permissions.extend(analyzer.permissions)
        
        # 额外检查：敏感字符串
        self._check_sensitive_strings(file_path, source)
    
    def _check_sensitive_strings(self, file_path: str, source: str) -> None:
        """检查源代码中的敏感字符串"""
        lines = source.split("\n")
        
        # 硬编码密钥/API Key 模式
        key_patterns = [
            (r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', "硬编码 API Key"),
            (r'["\']?(?:secret[_-]?key|secretkey)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', "硬编码 Secret Key"),
            (r'["\']?(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{4,})["\']', "硬编码密码"),
            (r'["\']?(?:token|auth_token)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', "硬编码 Token"),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, desc in key_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self._issues.append(CodeIssue(
                        severity=RiskLevel.HIGH,
                        category="secrets",
                        message=f"发现{desc}",
                        file=file_path,
                        line=line_num,
                        code=line.strip()[:100],
                        fix_suggestion="使用环境变量或密钥管理服务存储敏感信息",
                    ))
    
    def _check_dependencies(self, skill_path: str) -> None:
        """检查依赖包安全"""
        requirements_file = os.path.join(skill_path, "requirements.txt")
        
        if not os.path.exists(requirements_file):
            return
        
        try:
            with open(requirements_file, "r", encoding="utf-8") as f:
                requirements = f.read()
        except Exception:
            return
        
        # 解析依赖
        dependencies = self._parse_requirements(requirements)
        
        # 检查每个依赖
        for pkg_name, version in dependencies.items():
            if self.vuln_db:
                vulns = self.vuln_db.check_package_vulnerable(pkg_name, version)
                for vuln in vulns:
                    self._issues.append(CodeIssue(
                        severity=RiskLevel(vuln.severity.lower()),
                        category="dependency",
                        message=f"依赖包 {pkg_name}@{version} 存在漏洞: {vuln.name}",
                        file=requirements_file,
                        line=0,
                        code=f"{pkg_name}=={version}",
                        fix_suggestion=vuln.fix_action,
                    ))
    
    def _parse_requirements(self, requirements: str) -> Dict[str, str]:
        """解析 requirements.txt"""
        deps = {}
        for line in requirements.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # 解析包名和版本
            if "==" in line:
                parts = line.split("==")
                deps[parts[0].strip()] = parts[1].strip()
            elif ">=" in line:
                parts = line.split(">=")
                deps[parts[0].strip()] = parts[1].strip()
            else:
                deps[line] = "*"
        
        return deps
    
    def _verify_signature(self, skill_path: str) -> Optional[bool]:
        """验证代码签名"""
        signature_file = os.path.join(skill_path, ".signature")
        
        if not os.path.exists(signature_file):
            return None  # 未签名
        
        try:
            with open(signature_file, "r") as f:
                signature_data = json.load(f)
            
            # 简化验证：检查哈希是否匹配
            expected_hash = signature_data.get("hash")
            if not expected_hash:
                return False
            
            # 计算实际哈希
            actual_hash = self._calculate_directory_hash(skill_path)
            
            return expected_hash == actual_hash
        except Exception:
            return False
    
    def _calculate_directory_hash(self, directory: str) -> str:
        """计算目录哈希"""
        hasher = hashlib.sha256()
        
        for root, _, files in os.walk(directory):
            for file in sorted(files):
                if file == ".signature":
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "rb") as f:
                        hasher.update(f.read())
                except Exception:
                    pass
        
        return hasher.hexdigest()
    
    def _calculate_trust_level(self, skill_name: str, issue_count: int) -> str:
        """计算信任级别"""
        # 基于问题数量和名称推断
        if issue_count == 0:
            return "trusted"
        elif issue_count <= 2:
            return "verified"
        elif issue_count <= 5:
            return "community"
        else:
            return "unverified"
    
    def _generate_permissions_summary(self) -> str:
        """生成权限摘要"""
        if not self._permissions:
            return "无特殊权限"
        
        high_risk = [p for p in self._permissions if p.risk_level == RiskLevel.CRITICAL]
        if high_risk:
            return f"需要 {len(high_risk)} 个高危权限"
        
        return f"需要 {len(self._permissions)} 个权限"
    
    def _generate_network_summary(self) -> str:
        """生成网络调用摘要"""
        if not self._network_calls:
            return "无网络调用"
        
        external = [c for c in self._network_calls if c.is_external]
        unencrypted = [c for c in self._network_calls if not c.is_encrypted]
        
        parts = [f"{len(self._network_calls)} 个网络调用"]
        if external:
            parts.append(f"{len(external)} 个外部请求")
        if unencrypted:
            parts.append(f"{len(unencrypted)} 个未加密")
        
        return ", ".join(parts)
    
    def _generate_file_summary(self) -> str:
        """生成文件操作摘要"""
        if not self._file_operations:
            return "无文件操作"
        
        sensitive = [f for f in self._file_operations if f.is_sensitive]
        write_ops = [f for f in self._file_operations if f.operation in ("write", "delete")]
        
        parts = [f"{len(self._file_operations)} 个文件操作"]
        if write_ops:
            parts.append(f"{len(write_ops)} 个写入/删除")
        if sensitive:
            parts.append(f"{len(sensitive)} 个敏感路径")
        
        return ", ".join(parts)
    
    def _generate_details(self) -> Dict[str, Any]:
        """生成详细报告"""
        return {
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "file": i.file,
                    "line": i.line,
                    "code": i.code,
                    "fix_suggestion": i.fix_suggestion,
                }
                for i in self._issues
            ],
            "network_calls": [
                {
                    "url": n.url,
                    "method": n.method,
                    "is_external": n.is_external,
                    "is_encrypted": n.is_encrypted,
                    "line": n.line,
                }
                for n in self._network_calls
            ],
            "file_operations": [
                {
                    "path": f.path,
                    "operation": f.operation,
                    "is_sensitive": f.is_sensitive,
                    "line": f.line,
                }
                for f in self._file_operations
            ],
            "permissions": [
                {
                    "permission": p.permission,
                    "description": p.description,
                    "risk_level": p.risk_level.value,
                    "line": p.line,
                }
                for p in self._permissions
            ],
        }


class ASTSecurityAnalyzer(ast.NodeVisitor):
    """AST 安全分析器"""
    
    def __init__(
        self,
        file_path: str,
        source: str,
        dangerous_functions: Dict,
        network_libs: Dict,
        file_operations: Dict,
    ):
        self.file_path = file_path
        self.source = source
        self.lines = source.split("\n")
        self.dangerous_functions = dangerous_functions
        self.network_libs = network_libs
        self.file_operations = file_operations
        
        self.issues: List[CodeIssue] = []
        self.network_calls: List[NetworkCall] = []
        self.file_operations: List[FileOperation] = []
        self.permissions: List[PermissionUsage] = []
        
        # 跟踪导入
        self.imports: Dict[str, str] = {}  # alias -> full_name
    
    def visit_Import(self, node: ast.Import) -> None:
        """处理 import 语句"""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imports[asname] = name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """处理 from ... import 语句"""
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            full_name = f"{module}.{name}" if module else name
            self.imports[asname] = full_name
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """处理函数调用"""
        func_name = self._get_call_name(node)
        line_num = node.lineno
        line_content = self.lines[line_num - 1] if line_num <= len(self.lines) else ""
        
        # 检查危险函数
        self._check_dangerous_call(func_name, node, line_num, line_content)
        
        # 检查网络调用
        self._check_network_call(func_name, node, line_num)
        
        # 检查文件操作
        self._check_file_operation(func_name, node, line_num)
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """获取函数调用的完整名称"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""
    
    def _check_dangerous_call(
        self,
        func_name: str,
        node: ast.Call,
        line_num: int,
        line_content: str,
    ) -> None:
        """检查危险函数调用"""
        # 解析完整名称
        full_name = self._resolve_name(func_name)
        
        # 检查是否在黑名单中
        for dangerous_name, info in self.dangerous_functions.items():
            if full_name == dangerous_name or func_name == dangerous_name.split(".")[-1]:
                self.issues.append(CodeIssue(
                    severity=info["severity"],
                    category="dangerous_function",
                    message=f"调用危险函数: {dangerous_name} - {info['desc']}",
                    file=self.file_path,
                    line=line_num,
                    code=line_content.strip()[:100],
                    fix_suggestion=f"避免使用 {dangerous_name}，考虑使用更安全的替代方案",
                ))
    
    def _check_network_call(self, func_name: str, node: ast.Call, line_num: int) -> None:
        """检查网络调用"""
        full_name = self._resolve_name(func_name)
        
        # 检查是否是网络请求
        for lib, methods in self.network_libs.items():
            if any(full_name.endswith(f"{lib}.{m}") or full_name == m for m in methods):
                # 提取 URL
                url = self._extract_url_from_call(node)
                is_https = url.startswith("https://") if url else False
                is_external = not any(
                    url.startswith(prefix) for prefix in ["http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1"]
                ) if url else True
                
                self.network_calls.append(NetworkCall(
                    url=url or "unknown",
                    method=func_name.split(".")[-1].upper(),
                    is_external=is_external,
                    is_encrypted=is_https,
                    line=line_num,
                ))
    
    def _check_file_operation(self, func_name: str, node: ast.Call, line_num: int) -> None:
        """检查文件操作"""
        full_name = self._resolve_name(func_name)
        
        # 检查 open() 调用
        if func_name == "open" or full_name.endswith("open"):
            # 提取文件路径
            path = self._extract_first_arg(node)
            mode = "read"
            
            # 检查 open 的 mode 参数
            if len(node.args) >= 2:
                mode_arg = node.args[1]
                if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                    mode_str = mode_arg.value
                    if "w" in mode_str or "a" in mode_str or "x" in mode_str:
                        mode = "write"
                    elif "r" in mode_str:
                        mode = "read"
            
            is_sensitive = self._is_sensitive_path(str(path))
            
            self.file_operations.append(FileOperation(
                path=str(path)[:100],
                operation=mode,
                is_sensitive=is_sensitive,
                line=line_num,
            ))
            
            if is_sensitive:
                self.issues.append(CodeIssue(
                    severity=RiskLevel.HIGH,
                    category="file_operation",
                    message=f"访问敏感路径: {path}",
                    file=self.file_path,
                    line=line_num,
                    code=self.lines[line_num - 1].strip()[:100],
                    fix_suggestion="确认是否需要访问此敏感路径",
                ))
    
    def _resolve_name(self, name: str) -> str:
        """解析名称到完整路径"""
        if "." in name:
            parts = name.split(".")
            base = parts[0]
            if base in self.imports:
                return self.imports[base] + "." + ".".join(parts[1:])
        else:
            if name in self.imports:
                return self.imports[name]
        return name
    
    def _extract_url_from_call(self, node: ast.Call) -> str:
        """从调用中提取 URL"""
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
            elif isinstance(first_arg, ast.Str):  # Python < 3.8
                return first_arg.s
        return ""
    
    def _extract_first_arg(self, node: ast.Call) -> str:
        """提取第一个参数"""
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant):
                return str(first_arg.value)
            elif isinstance(first_arg, ast.Str):  # Python < 3.8
                return first_arg.s
        return ""
    
    def _is_sensitive_path(self, path: str) -> bool:
        """检查是否是敏感路径"""
        for pattern in SkillSecurityScanner.SENSITIVE_PATHS:
            if re.match(pattern, path, re.IGNORECASE):
                return True
        return False
