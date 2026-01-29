"""
配置和节点相关的数据模型

定义系统配置、节点信息等数据结构
"""
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    """配置模型"""
    config_id: Optional[str] = None  # 配置 ID
    key: str  # 配置键
    value: Any  # 配置值
    description: str  # 配置描述
    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间


class NodeModel(BaseModel):
    """节点模型"""
    node_id: str  # 节点 ID
    node_type: str  # 节点类型
    status: str = "active"  # 节点状态
    last_heartbeat: datetime = Field(default_factory=datetime.now)  # 最后心跳时间
    task_count: int = 0  # 任务计数
    capabilities: Dict = Field(default_factory=dict)  # 节点能力
