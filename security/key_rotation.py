"""
密钥轮换管理器

提供自动化的密钥轮换功能：
- API Key 自动轮换
- 认证令牌轮换
- 轮换历史记录
- 到期提醒
- 紧急撤销
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class KeyType(Enum):
    """密钥类型"""
    API_KEY = "api_key"
    AUTH_TOKEN = "auth_token"
    PASSWORD = "password"
    CERTIFICATE = "certificate"


class RotationStatus(Enum):
    """轮换状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class KeyRotationRecord:
    """密钥轮换记录"""
    key_id: str
    key_type: str
    old_value_hash: str  # 旧密钥的哈希（不存储明文）
    new_value_hash: str  # 新密钥的哈希
    rotated_at: str
    expires_at: Optional[str] = None
    rotated_by: str = "system"
    reason: str = ""
    status: str = RotationStatus.ACTIVE.value


@dataclass
class KeyMetadata:
    """密钥元数据"""
    key_id: str
    key_type: str
    name: str
    description: str
    created_at: str
    last_rotated_at: Optional[str] = None
    expires_at: Optional[str] = None
    rotation_interval_days: int = 90
    auto_rotate: bool = False
    status: str = RotationStatus.ACTIVE.value


class KeyRotationManager:
    """
    密钥轮换管理器
    
    功能：
    1. 管理密钥轮换计划
    2. 自动轮换 API Key 和认证令牌
    3. 记录轮换历史
    4. 发送到期提醒
    5. 紧急撤销密钥
    """
    
    CONFIG_DIR = os.path.expanduser("~/.openclaw")
    ROTATION_DB_PATH = os.path.join(CONFIG_DIR, "key_rotation_db.json")
    ROTATION_HISTORY_PATH = os.path.join(CONFIG_DIR, "key_rotation_history.json")
    
    # 默认轮换周期（天）
    DEFAULT_ROTATION_INTERVAL = 90
    
    # 到期提醒阈值（天）
    EXPIRY_WARNING_DAYS = [30, 14, 7, 1]
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(self.CONFIG_DIR, "openclaw.json")
        self.config_dir = os.path.dirname(self.config_path)
        self._ensure_db_dir()
        self._metadata: Dict[str, KeyMetadata] = {}
        self._history: List[KeyRotationRecord] = []
        self._load_data()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def _load_data(self):
        """加载轮换数据"""
        # 加载元数据
        if os.path.exists(self.ROTATION_DB_PATH):
            try:
                with open(self.ROTATION_DB_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key_id, meta_dict in data.get("metadata", {}).items():
                        self._metadata[key_id] = KeyMetadata(**meta_dict)
            except Exception:
                pass
        
        # 加载历史记录
        if os.path.exists(self.ROTATION_HISTORY_PATH):
            try:
                with open(self.ROTATION_HISTORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for record_dict in data.get("history", []):
                        self._history.append(KeyRotationRecord(**record_dict))
            except Exception:
                pass
    
    def _save_data(self):
        """保存轮换数据"""
        # 保存元数据
        meta_data = {
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                key_id: asdict(meta) for key_id, meta in self._metadata.items()
            }
        }
        with open(self.ROTATION_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
        
        # 保存历史记录
        history_data = {
            "updated_at": datetime.now().isoformat(),
            "history": [asdict(record) for record in self._history[-100:]],  # 只保留最近 100 条
        }
        with open(self.ROTATION_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    # --- 密钥注册和管理 ---
    
    def register_key(
        self,
        key_id: str,
        key_type: KeyType,
        name: str,
        description: str = "",
        rotation_interval_days: int = 90,
        auto_rotate: bool = False,
    ) -> Dict[str, Any]:
        """
        注册密钥到轮换管理系统
        
        Args:
            key_id: 密钥标识符
            key_type: 密钥类型
            name: 密钥名称
            description: 密钥描述
            rotation_interval_days: 轮换周期（天）
            auto_rotate: 是否自动轮换
            
        Returns:
            注册结果
        """
        if key_id in self._metadata:
            return {
                "success": False,
                "message": f"密钥 {key_id} 已存在",
            }
        
        now = datetime.now()
        expires_at = now + timedelta(days=rotation_interval_days)
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type.value,
            name=name,
            description=description,
            created_at=now.isoformat(),
            rotation_interval_days=rotation_interval_days,
            auto_rotate=auto_rotate,
            expires_at=expires_at.isoformat(),
        )
        
        self._metadata[key_id] = metadata
        self._save_data()
        
        return {
            "success": True,
            "message": f"密钥 {key_id} 已注册",
            "metadata": asdict(metadata),
        }
    
    def unregister_key(self, key_id: str) -> Dict[str, Any]:
        """注销密钥"""
        if key_id not in self._metadata:
            return {
                "success": False,
                "message": f"密钥 {key_id} 不存在",
            }
        
        del self._metadata[key_id]
        self._save_data()
        
        return {
            "success": True,
            "message": f"密钥 {key_id} 已注销",
        }
    
    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """获取密钥元数据"""
        return self._metadata.get(key_id)
    
    def list_keys(self) -> List[KeyMetadata]:
        """列出所有管理的密钥"""
        return list(self._metadata.values())
    
    # --- 密钥轮换 ---
    
    def rotate_key(
        self,
        key_id: str,
        reason: str = "scheduled",
        manual_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行密钥轮换
        
        Args:
            key_id: 密钥标识符
            reason: 轮换原因
            manual_value: 手动指定的新密钥值（可选）
            
        Returns:
            轮换结果，包含新密钥
        """
        metadata = self._metadata.get(key_id)
        if not metadata:
            return {
                "success": False,
                "message": f"密钥 {key_id} 未注册",
            }
        
        # 获取当前密钥值
        current_value = self._get_current_key_value(key_id)
        
        # 生成新密钥
        if manual_value:
            new_value = manual_value
        else:
            new_value = self._generate_new_key(metadata.key_type)
        
        # 计算哈希
        old_hash = self._hash_key(current_value) if current_value else ""
        new_hash = self._hash_key(new_value)
        
        # 更新配置
        update_result = self._update_key_in_config(key_id, new_value)
        if not update_result["success"]:
            return update_result
        
        # 创建轮换记录
        now = datetime.now()
        expires_at = now + timedelta(days=metadata.rotation_interval_days)
        
        record = KeyRotationRecord(
            key_id=key_id,
            key_type=metadata.key_type,
            old_value_hash=old_hash,
            new_value_hash=new_hash,
            rotated_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            reason=reason,
        )
        
        # 更新元数据
        metadata.last_rotated_at = now.isoformat()
        metadata.expires_at = expires_at.isoformat()
        metadata.status = RotationStatus.ACTIVE.value
        
        # 保存历史
        self._history.append(record)
        self._save_data()
        
        return {
            "success": True,
            "message": f"密钥 {key_id} 已轮换",
            "new_value": new_value,
            "expires_at": expires_at.isoformat(),
            "warning": "请保存新密钥，此信息仅显示一次",
        }
    
    def auto_rotate_expired_keys(self) -> List[Dict[str, Any]]:
        """
        自动轮换所有到期的密钥
        
        Returns:
            轮换结果列表
        """
        results = []
        now = datetime.now()
        
        for key_id, metadata in self._metadata.items():
            if not metadata.auto_rotate:
                continue
            
            if metadata.expires_at:
                expires = datetime.fromisoformat(metadata.expires_at)
                if now >= expires:
                    result = self.rotate_key(key_id, reason="auto_expired")
                    results.append({
                        "key_id": key_id,
                        **result,
                    })
        
        return results
    
    def revoke_key(self, key_id: str, reason: str = "") -> Dict[str, Any]:
        """
        紧急撤销密钥
        
        Args:
            key_id: 密钥标识符
            reason: 撤销原因
            
        Returns:
            撤销结果
        """
        metadata = self._metadata.get(key_id)
        if not metadata:
            return {
                "success": False,
                "message": f"密钥 {key_id} 未注册",
            }
        
        # 生成新的随机密钥（使旧密钥失效）
        new_value = self._generate_new_key(metadata.key_type)
        
        # 更新配置
        update_result = self._update_key_in_config(key_id, new_value)
        if not update_result["success"]:
            return update_result
        
        # 更新状态
        metadata.status = RotationStatus.REVOKED.value
        
        # 记录撤销
        record = KeyRotationRecord(
            key_id=key_id,
            key_type=metadata.key_type,
            old_value_hash=self._hash_key("revoked"),
            new_value_hash=self._hash_key(new_value),
            rotated_at=datetime.now().isoformat(),
            reason=f"revoked: {reason}",
            status=RotationStatus.REVOKED.value,
        )
        self._history.append(record)
        self._save_data()
        
        return {
            "success": True,
            "message": f"密钥 {key_id} 已紧急撤销并替换",
            "warning": "所有使用该密钥的服务需要更新配置",
        }
    
    # --- 到期提醒 ---
    
    def check_expiring_keys(self) -> List[Dict[str, Any]]:
        """
        检查即将到期的密钥
        
        Returns:
            即将到期的密钥列表
        """
        expiring = []
        now = datetime.now()
        
        for key_id, metadata in self._metadata.items():
            if metadata.status != RotationStatus.ACTIVE.value:
                continue
            
            if metadata.expires_at:
                expires = datetime.fromisoformat(metadata.expires_at)
                days_until_expiry = (expires - now).days
                
                if days_until_expiry <= 0:
                    expiring.append({
                        "key_id": key_id,
                        "name": metadata.name,
                        "status": "expired",
                        "days_overdue": abs(days_until_expiry),
                        "expires_at": metadata.expires_at,
                    })
                elif days_until_expiry in self.EXPIRY_WARNING_DAYS:
                    expiring.append({
                        "key_id": key_id,
                        "name": metadata.name,
                        "status": "warning",
                        "days_remaining": days_until_expiry,
                        "expires_at": metadata.expires_at,
                    })
        
        return expiring
    
    def get_rotation_recommendations(self) -> List[Dict[str, Any]]:
        """
        获取轮换建议
        
        Returns:
            建议轮换的密钥列表
        """
        recommendations = []
        now = datetime.now()
        
        for key_id, metadata in self._metadata.items():
            if metadata.status != RotationStatus.ACTIVE.value:
                continue
            
            # 检查是否超过轮换周期
            if metadata.last_rotated_at:
                last_rotated = datetime.fromisoformat(metadata.last_rotated_at)
                days_since_rotation = (now - last_rotated).days
                
                if days_since_rotation >= metadata.rotation_interval_days:
                    recommendations.append({
                        "key_id": key_id,
                        "name": metadata.name,
                        "reason": "超过轮换周期",
                        "days_since_rotation": days_since_rotation,
                        "recommended_action": "rotate",
                    })
            
            # 检查是否即将到期
            if metadata.expires_at:
                expires = datetime.fromisoformat(metadata.expires_at)
                days_until_expiry = (expires - now).days
                
                if days_until_expiry <= 7:
                    recommendations.append({
                        "key_id": key_id,
                        "name": metadata.name,
                        "reason": f"{days_until_expiry} 天后到期",
                        "days_until_expiry": days_until_expiry,
                        "recommended_action": "rotate",
                    })
        
        return recommendations
    
    # --- 历史记录 ---
    
    def get_rotation_history(
        self,
        key_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[KeyRotationRecord]:
        """
        获取轮换历史
        
        Args:
            key_id: 筛选特定密钥
            limit: 返回记录数限制
            
        Returns:
            轮换记录列表
        """
        records = self._history
        
        if key_id:
            records = [r for r in records if r.key_id == key_id]
        
        # 按时间倒序
        records = sorted(records, key=lambda r: r.rotated_at, reverse=True)
        
        return records[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取轮换统计信息"""
        total_keys = len(self._metadata)
        active_keys = len([m for m in self._metadata.values() if m.status == RotationStatus.ACTIVE.value])
        expired_keys = len([m for m in self._metadata.values() if m.status == RotationStatus.EXPIRED.value])
        revoked_keys = len([m for m in self._metadata.values() if m.status == RotationStatus.REVOKED.value])
        
        # 按类型统计
        by_type = {}
        for meta in self._metadata.values():
            by_type[meta.key_type] = by_type.get(meta.key_type, 0) + 1
        
        # 最近轮换次数
        recent_rotations = len([
            r for r in self._history
            if datetime.now() - datetime.fromisoformat(r.rotated_at) <= timedelta(days=30)
        ])
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "revoked_keys": revoked_keys,
            "by_type": by_type,
            "recent_rotations_30d": recent_rotations,
            "total_rotation_records": len(self._history),
        }
    
    # --- 内部方法 ---
    
    def _get_current_key_value(self, key_id: str) -> Optional[str]:
        """从配置中获取当前密钥值"""
        cfg = self._load_config()
        
        # 根据 key_id 解析配置路径
        if key_id == "gateway_auth_token":
            return cfg.get("gateway", {}).get("auth", {}).get("token")
        elif key_id.startswith("api_key_"):
            provider = key_id.replace("api_key_", "")
            return cfg.get("models", {}).get("providers", {}).get(provider, {}).get("apiKey")
        
        return None
    
    def _update_key_in_config(self, key_id: str, new_value: str) -> Dict[str, Any]:
        """更新配置文件中的密钥"""
        cfg = self._load_config()
        
        # 根据 key_id 更新配置
        if key_id == "gateway_auth_token":
            if "gateway" not in cfg:
                cfg["gateway"] = {}
            if "auth" not in cfg["gateway"]:
                cfg["gateway"]["auth"] = {}
            cfg["gateway"]["auth"]["token"] = new_value
        
        elif key_id.startswith("api_key_"):
            provider = key_id.replace("api_key_", "")
            if "models" not in cfg:
                cfg["models"] = {}
            if "providers" not in cfg["models"]:
                cfg["models"]["providers"] = {}
            if provider not in cfg["models"]["providers"]:
                cfg["models"]["providers"][provider] = {}
            cfg["models"]["providers"][provider]["apiKey"] = new_value
        
        else:
            return {
                "success": False,
                "message": f"未知的密钥类型: {key_id}",
            }
        
        # 保存配置
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "message": f"保存配置失败: {str(e)}",
            }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _generate_new_key(self, key_type: str) -> str:
        """生成新密钥"""
        if key_type == KeyType.API_KEY.value:
            # API Key: sk- 前缀 + 随机字符串
            return f"sk-{secrets.token_urlsafe(32)}"
        elif key_type == KeyType.AUTH_TOKEN.value:
            # 认证令牌: 32 字节随机
            return secrets.token_urlsafe(32)
        elif key_type == KeyType.PASSWORD.value:
            # 密码: 16 位随机
            return secrets.token_urlsafe(16)
        else:
            return secrets.token_urlsafe(32)
    
    def _hash_key(self, key: str) -> str:
        """计算密钥哈希"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]


# --- 便捷函数 ---

def rotate_gateway_token(reason: str = "manual") -> Dict[str, Any]:
    """便捷函数：轮换 Gateway 认证令牌"""
    manager = KeyRotationManager()
    
    # 确保已注册
    if "gateway_auth_token" not in [m.key_id for m in manager.list_keys()]:
        manager.register_key(
            key_id="gateway_auth_token",
            key_type=KeyType.AUTH_TOKEN,
            name="Gateway 认证令牌",
            description="OpenClaw Gateway 访问令牌",
            auto_rotate=False,
        )
    
    return manager.rotate_key("gateway_auth_token", reason=reason)


def rotate_api_key(provider: str, reason: str = "manual") -> Dict[str, Any]:
    """便捷函数：轮换 API Key"""
    manager = KeyRotationManager()
    key_id = f"api_key_{provider}"
    
    # 确保已注册
    if key_id not in [m.key_id for m in manager.list_keys()]:
        manager.register_key(
            key_id=key_id,
            key_type=KeyType.API_KEY,
            name=f"{provider} API Key",
            description=f"{provider} 提供商的 API Key",
            auto_rotate=False,
        )
    
    return manager.rotate_key(key_id, reason=reason)


def check_key_health() -> Dict[str, Any]:
    """便捷函数：检查密钥健康状况"""
    manager = KeyRotationManager()
    
    return {
        "expiring_keys": manager.check_expiring_keys(),
        "recommendations": manager.get_rotation_recommendations(),
        "statistics": manager.get_statistics(),
    }
