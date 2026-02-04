from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ParsingRule(BaseModel):
    """网站解析规则模型"""
    id: Optional[str] = None
    domain: str  # 匹配域名，支持通配符或精确匹配
    parser_type: str  # gne, llm, xpath
    parser_config: Dict[str, Any] = Field(default_factory=dict) # 解析配置
    cookies: Optional[str] = ""  # 网站 Cookies
    description: Optional[str] = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ParsingRuleCreate(BaseModel):
    domain: str
    parser_type: str
    parser_config: Dict[str, Any] = Field(default_factory=dict)
    cookies: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool = True

class ParsingRuleUpdate(BaseModel):
    domain: Optional[str] = None
    parser_type: Optional[str] = None
    parser_config: Optional[Dict[str, Any]] = None
    cookies: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
