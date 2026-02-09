from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.task import ScrapeParams, CacheConfig, StorageType

class ParsingRule(BaseModel):
    """网站解析规则模型"""
    id: Optional[str] = None
    domain: str  # 匹配域名，支持通配符或精确匹配
    parser_type: str  # gne, llm, xpath
    parser_config: Dict[str, Any] = Field(default_factory=dict) # 解析配置
    
    # 浏览器特征配置
    engine: Optional[str] = "playwright"
    wait_for: Optional[str] = "networkidle"
    timeout: Optional[int] = 30000
    viewport: Optional[Dict[str, int]] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    stealth: Optional[bool] = True
    save_html: Optional[bool] = True
    screenshot: Optional[bool] = False
    is_fullscreen: Optional[bool] = False
    block_images: Optional[bool] = False
    
    # 高级配置
    intercept_apis: Optional[list] = Field(default_factory=list)
    intercept_continue: Optional[bool] = True
    proxy: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"server": "", "username": "", "password": ""})
    
    # 存储配置
    storage_type: StorageType = StorageType.MONGO
    mongo_collection: Optional[str] = None
    oss_path: Optional[str] = None
    
    cache_config: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"enabled": True, "ttl": 3600}) # 缓存/去重配置
    cookies: Optional[str] = ""  # 网站 Cookies
    description: Optional[str] = ""
    is_active: bool = True
    priority: int = 5  # 优先级，数字越大优先级越高
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ParsingRuleCreate(BaseModel):
    domain: str
    parser_type: str
    parser_config: Dict[str, Any] = Field(default_factory=dict)
    
    # 浏览器特征配置
    engine: Optional[str] = "playwright"
    wait_for: Optional[str] = "networkidle"
    timeout: Optional[int] = 30000
    viewport: Optional[Dict[str, int]] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    stealth: Optional[bool] = True
    save_html: Optional[bool] = True
    screenshot: Optional[bool] = False
    is_fullscreen: Optional[bool] = False
    block_images: Optional[bool] = False
    
    # 高级配置
    intercept_apis: Optional[list] = Field(default_factory=list)
    intercept_continue: Optional[bool] = True
    proxy: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"server": "", "username": "", "password": ""})
    
    # 存储配置
    storage_type: Optional[StorageType] = StorageType.MONGO
    mongo_collection: Optional[str] = None
    oss_path: Optional[str] = None
    
    cache_config: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"enabled": True, "ttl": 3600})
    cookies: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool = True
    priority: int = 5

class ParsingRuleUpdate(BaseModel):
    domain: Optional[str] = None
    parser_type: Optional[str] = None
    parser_config: Optional[Dict[str, Any]] = None
    
    # 浏览器特征配置
    engine: Optional[str] = None
    wait_for: Optional[str] = None
    timeout: Optional[int] = None
    viewport: Optional[Dict[str, int]] = None
    stealth: Optional[bool] = None
    save_html: Optional[bool] = None
    screenshot: Optional[bool] = None
    is_fullscreen: Optional[bool] = None
    block_images: Optional[bool] = None
    
    # 高级配置
    intercept_apis: Optional[list] = None
    intercept_continue: Optional[bool] = None
    proxy: Optional[Dict[str, Any]] = None
    
    # 存储配置
    storage_type: Optional[StorageType] = None
    mongo_collection: Optional[str] = None
    oss_path: Optional[str] = None
    
    cache_config: Optional[Dict[str, Any]] = None
    cookies: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
