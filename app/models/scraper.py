from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from bson import ObjectId
from app.models.common import PyObjectId
from app.models.task import StorageType

class ScraperBase(BaseModel):
    name: str = Field(..., description="任务名称")
    url: HttpUrl = Field(..., description="起始 URL")
    rule_id: Optional[str] = Field(None, description="关联的详情页解析规则 ID")
    description: Optional[str] = Field(None, description="描述")
    
    # 列表提取规则
    list_xpath: str = Field(..., description="列表项容器 XPath")
    title_xpath: str = Field(..., description="标题 XPath (相对于列表项)")
    link_xpath: str = Field(..., description="链接 XPath (相对于列表项)")
    time_xpath: Optional[str] = Field(None, description="发布时间 XPath (相对于列表项)")
    
    # 翻页规则
    pagination_next_xpath: Optional[str] = Field(None, description="下一页按钮 XPath")
    max_pages: int = Field(1, ge=1, description="最大采集页数")
    
    # 兼容前端的嵌套结构
    params: Dict[str, Any] = Field(default_factory=dict, description="抓取参数")
    cache: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "ttl": 3600}, description="缓存配置")
    
    # 浏览器通用配置 (同步自 ScrapeParams)
    engine: str = Field("playwright", description="浏览器引擎: playwright, drissionpage")
    wait_for: str = Field("networkidle", description="等待策略: networkidle, load, domcontentloaded")
    wait_time: int = Field(3000, description="额外等待时间（毫秒）")
    wait_timeout: int = Field(30000, description="等待超时时间(ms)")
    wait_for_selector: Optional[str] = Field(None, description="等待元素选择器")
    user_agent: Optional[str] = Field(None, description="自定义 User-Agent")
    
    viewport: Dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080}, description="视口大小")
    stealth: bool = Field(True, description="是否启用反检测 (stealth)")
    no_images: bool = Field(True, description="不加载图片")
    no_css: bool = Field(True, description="不加载 CSS")
    block_images: bool = Field(False, description="是否拦截图片")
    block_media: bool = Field(False, description="是否拦截媒体资源")
    
    # 高级配置
    proxy: Optional[Dict[str, Any]] = Field(None, description="代理配置 {server, username, password}")
    proxy_pool_group: Optional[str] = Field(None, description="代理池分组")
    cookies: Optional[Union[str, List[Dict[str, Any]], Dict[str, str]]] = Field(None, description="Cookies")
    intercept_apis: Optional[List[str]] = Field(None, description="要拦截的接口 URL 模式列表")
    intercept_continue: bool = Field(False, description="拦截接口后是否继续请求")
    
    # 存储与截图
    storage_type: StorageType = Field(StorageType.MONGO, description="存储位置: mongo, oss")
    mongo_collection: Optional[str] = Field(None, description="自定义 MongoDB 表名")
    oss_path: Optional[str] = Field(None, description="自定义 OSS 存储路径")
    save_html: bool = Field(True, description="是否保存 HTML 源码")
    screenshot: bool = Field(False, description="是否截图")
    is_fullscreen: bool = Field(False, description="是否全屏截图")
    
    max_retries: int = Field(2, ge=0, description="列表加载失败重试次数")
    
    # 定时设置
    cron: Optional[str] = Field(None, description="Cron 表达式 (例如: 0 0 * * *)")
    enabled_schedule: bool = Field(False, description="是否启用定时采集")
    last_run_at: Optional[datetime] = Field(None, description="最后一次定时执行时间")
    next_run_at: Optional[datetime] = Field(None, description="下一次预计执行时间")
    enabled: bool = Field(True, description="站点是否启用")

class ScraperCreate(ScraperBase):
    pass

class ScraperUpdate(ScraperBase):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    list_xpath: Optional[str] = None
    title_xpath: Optional[str] = None
    link_xpath: Optional[str] = None

class ScraperResponse(ScraperBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ScraperTestRequest(BaseModel):
    url: HttpUrl
    list_xpath: str
    title_xpath: str
    link_xpath: str
    time_xpath: Optional[str] = None
    pagination_next_xpath: Optional[str] = None
    engine: str = "playwright"
    wait_for: str = "networkidle"
    wait_time: int = 3000
    wait_for_selector: Optional[str] = None
    user_agent: Optional[str] = None
    wait_timeout: Optional[int] = 30000
    block_images: bool = True
    no_css: bool = True
    stealth: bool = True
    max_retries: int = 2
    proxy: Optional[Dict[str, Any]] = None
    proxy_pool_group: Optional[str] = None
    cookies: Optional[Union[str, List[Dict[str, Any]], Dict[str, str]]] = None

class AiRuleGenerationRequest(BaseModel):
    url: HttpUrl
    wait_for_selector: Optional[str] = None
    timeout: int = 30000
    proxy: Optional[Dict[str, Any]] = None
    proxy_pool_group: Optional[str] = None
    cookies: Optional[Union[str, List[Dict[str, Any]], Dict[str, str]]] = None
