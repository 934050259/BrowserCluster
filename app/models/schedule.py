"""
定时任务相关的数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl
from app.models.task import ScrapeParams, CacheConfig


class ScheduleStatus(str, Enum):
    """定时任务状态枚举"""
    ACTIVE = "active"  # 激活中
    PAUSED = "paused"  # 已暂停


class ScheduleType(str, Enum):
    """调度类型"""
    INTERVAL = "interval"  # 间隔执行 (秒/分/时/天)
    CRON = "cron"          # Cron 表达式


class ScheduleModel(BaseModel):
    """定时任务模型"""
    schedule_id: Optional[str] = None  # 调度 ID
    name: str  # 任务名称
    description: Optional[str] = None  # 任务描述
    url: HttpUrl  # 目标 URL
    params: ScrapeParams = Field(default_factory=ScrapeParams)  # 抓取参数
    cache: CacheConfig = Field(default_factory=CacheConfig)  # 缓存配置
    priority: int = 1  # 任务优先级
    
    # 调度策略
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    interval: Optional[int] = None  # 间隔时间（秒），用于 INTERVAL 类型
    cron: Optional[str] = None  # Cron 表达式，用于 CRON 类型
    
    status: ScheduleStatus = ScheduleStatus.ACTIVE  # 状态
    last_run: Optional[datetime] = None  # 最近一次运行时间
    next_run: Optional[datetime] = None  # 下一次运行时间
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间


class ScheduleCreate(BaseModel):
    """创建定时任务请求模型"""
    name: str
    description: Optional[str] = None
    url: HttpUrl
    params: ScrapeParams = Field(default_factory=ScrapeParams)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    priority: int = 1
    schedule_type: ScheduleType
    interval: Optional[int] = None
    cron: Optional[str] = None


class ScheduleUpdate(BaseModel):
    """更新定时任务请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    params: Optional[ScrapeParams] = None
    cache: Optional[CacheConfig] = None
    priority: Optional[int] = None
    schedule_type: Optional[ScheduleType] = None
    interval: Optional[int] = None
    cron: Optional[str] = None
    status: Optional[ScheduleStatus] = None
