"""
任务相关的数据模型

定义任务请求、响应、状态等数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, HttpUrl, Field


class ScrapeParams(BaseModel):
    """抓取参数模型"""
    wait_for: str = "networkidle"  # 等待策略: networkidle, load, domcontentloaded
    wait_time: int = 3000  # 额外等待时间（毫秒）
    timeout: int = 30000  # 超时时间（毫秒）
    selector: Optional[str] = None  # 等待特定选择器（可选）
    screenshot: bool = False  # 是否截图
    is_fullscreen: bool = False  # 是否全屏截图
    block_images: bool = False  # 是否拦截图片
    block_media: bool = False  # 是否拦截媒体资源
    user_agent: Optional[str] = None  # 自定义 User-Agent
    viewport: Dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080})  # 视口大小
    proxy: Optional[Dict[str, Any]] = None  # 代理配置 {server, username, password}
    cookies: Optional[Union[str, List[Dict[str, Any]], Dict[str, str]]] = None  # Cookies, 支持 str, list [dict] 或 dict {name: value}
    stealth: bool = True  # 是否启用反检测 (stealth)
    intercept_apis: Optional[List[str]] = None  # 要拦截的接口 URL 模式列表
    intercept_continue: bool = False  # 拦截接口后是否继续请求 (默认 False)
    parser: Optional[str] = None  # 解析服务类型: gne, llm, xpath
    parser_config: Optional[Dict[str, Any]] = None  # 解析配置 (例如 LLM 需要解析的字段)


class CacheConfig(BaseModel):
    """缓存配置模型"""
    enabled: bool = True  # 是否启用缓存
    ttl: int = 3600  # 缓存过期时间（秒）


class ScrapeRequest(BaseModel):
    """抓取请求模型"""
    url: HttpUrl  # 目标 URL
    params: ScrapeParams = Field(default_factory=ScrapeParams)  # 抓取参数
    cache: CacheConfig = Field(default_factory=CacheConfig)  # 缓存配置
    priority: int = 1  # 任务优先级（数字越大优先级越高）
    schedule_id: Optional[str] = None  # 所属定时任务 ID (如果是定时任务触发的)


class TaskMetadata(BaseModel):
    """任务元数据模型"""
    title: Optional[str] = None  # 页面标题
    url: str  # 页面请求 URL
    actual_url: Optional[str] = None  # 实际加载的 URL (处理重定向后)
    load_time: float  # 加载时间（秒）
    timestamp: datetime = Field(default_factory=datetime.now)  # 时间戳


class ScrapedResult(BaseModel):
    """抓取结果模型"""
    html: Optional[str] = None  # 渲染后的 HTML (可选，支持字段投影优化)
    screenshot: Optional[str] = None  # 截图（base64 编码）
    metadata: Optional[TaskMetadata] = None  # 元数据
    intercepted_apis: Optional[Dict[str, List[Dict[str, Any]]]] = None  # 拦截到的接口数据 (键名中的 . 和 $ 已被转义为 _)
    parsed_data: Optional[Dict[str, Any]] = None  # HTML 解析后的结构化数据


class TaskError(BaseModel):
    """任务错误模型"""
    message: str  # 错误信息
    stack: Optional[str] = None  # 错误堆栈


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 等待中
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败


class TaskModel(BaseModel):
    """任务数据模型"""
    task_id: Optional[str] = None  # 任务 ID
    url: str  # 目标 URL
    status: TaskStatus = TaskStatus.PENDING  # 任务状态
    priority: int = 1  # 优先级
    params: Dict[str, Any] = Field(default_factory=dict)  # 抓取参数
    result: Optional[ScrapedResult] = None  # 抓取结果
    error: Optional[TaskError] = None  # 错误信息
    cache_key: Optional[str] = None  # 缓存键
    cached: bool = False  # 是否命中缓存
    node_id: Optional[str] = None  # 处理节点 ID
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间
    completed_at: Optional[datetime] = None  # 完成时间


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str  # 任务 ID
    url: str  # 目标 URL
    node_id: Optional[str] = None  # 处理节点 ID
    status: str  # 任务状态
    params: Optional[Dict[str, Any]] = None  # 抓取参数
    priority: Optional[int] = 1  # 优先级
    cache: Optional[Dict[str, Any]] = None  # 缓存配置
    result: Optional[ScrapedResult] = None  # 抓取结果
    error: Optional[TaskError] = None  # 错误信息
    cached: bool = False  # 是否来自缓存
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间
    completed_at: Optional[datetime] = None  # 完成时间


class BatchScrapeRequest(BaseModel):
    """批量抓取请求模型"""
    tasks: List[ScrapeRequest]  # 任务列表


class BatchScrapeResponse(BaseModel):
    """批量抓取响应模型"""
    task_ids: List[str]  # 任务 ID 列表


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型"""
    task_ids: List[str]  # 要删除的任务 ID 列表


class StatsResponse(BaseModel):
    """统计响应模型"""
    today: Dict[str, Any]  # 今日统计数据
    yesterday: Dict[str, Any]  # 昨日统计数据
    trends: Dict[str, float]  # 趋势百分比
    queue: Dict[str, Any]  # 队列统计数据
    history: List[Dict[str, Any]]  # 历史趋势数据
    nodes: Optional[Dict[str, Any]] = None  # 节点统计数据
    system_load: Optional[float] = 0.0  # 系统负载 (0-100)
