from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import json


class Cookie(BaseModel):
    """Cookie 模型"""
    id: str = Field(..., description="唯一标识，通常为 domain:username")
    domain: str = Field(..., description="所属域名")
    username: str = Field(..., description="账号标识")
    password: Optional[str] = Field(None, description="密码，用于自动登录")
    value: Dict[str, Any] = Field(..., description="Cookie 内容")
    status: str = Field("active", description="状态: active, inactive, invalid")
    group: str = Field("default", description="分组")
    
    # 频率控制
    rate_limit: int = Field(60, description="频率限制 (次/分钟)")
    
    # 统计信息
    fail_count: int = Field(0, description="连续失败次数")
    success_count: int = Field(0, description="累计成功次数")
    total_count: int = Field(0, description="累计使用次数")
    last_check_at: Optional[datetime] = Field(None, description="最后检测时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    @field_validator('value', mode='before')
    def parse_value(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    def to_redis_val(self) -> str:
        """转换为存储在 Redis 中的字符串格式 (JSON)"""
        return self.model_dump_json()

    @classmethod
    def from_redis_val(cls, val: str) -> "Cookie":
        """从 Redis 字符串格式解析"""
        return cls.model_validate_json(val)


class CookieCreate(BaseModel):
    """创建 Cookie 的请求模型"""
    domain: str
    username: str
    password: Optional[str] = None
    value: Dict[str, Any]
    group: str = "default"
    rate_limit: Optional[int] = None


class CookieUpdate(BaseModel):
    """更新 Cookie 的请求模型"""
    password: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    group: Optional[str] = None
    rate_limit: Optional[int] = None
    fail_count: Optional[int] = None


class CookieFilter(BaseModel):
    """Cookie 查询过滤器"""
    domain: Optional[str] = None
    group: Optional[str] = None
    status: Optional[str] = None


class CookieListResponse(BaseModel):
    """Cookie 列表响应"""
    total: int
    items: List[Cookie]


class CookieStats(BaseModel):
    """Cookie 统计信息"""
    total: int
    active: int
    invalid: int
    domains: List[str]
    groups: List[str]


class CookieConfig(BaseModel):
    """Cookie 检测配置模型"""
    cookie_enable_check: bool = Field(..., description="是否启用 Cookie 检测")
    cookie_check_interval: int = Field(..., description="Cookie 检测间隔（秒）")
    cookie_check_timeout: float = Field(..., description="Cookie 检测超时（秒）")
    cookie_fail_threshold: int = Field(..., description="Cookie 失效阈值")
    cookie_default_rate_limit: int = Field(..., description="默认 Cookie 调用频率限制 (次/分钟)")
