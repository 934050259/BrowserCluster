from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from bson import ObjectId
from app.models.common import PyObjectId

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
    
    # 浏览器配置
    wait_for_selector: Optional[str] = Field(None, description="等待元素选择器")
    wait_timeout: int = Field(30000, description="等待超时时间(ms)")
    no_images: bool = Field(True, description="不加载图片")
    no_css: bool = Field(True, description="不加载 CSS")

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
    wait_for_selector: Optional[str] = None
    wait_timeout: Optional[int] = 30000
    no_images: bool = True
    no_css: bool = True
