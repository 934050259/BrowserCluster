"""
HTML 解析服务模块

支持基于 gerapy-auto-extractor 和 LLM (Large Language Model) 的网页内容解析
"""
import json
import logging
from typing import Dict, Any, Optional, List
try:
    from gne import GeneralNewsExtractor, ListPageExtractor
    GNE_AVAILABLE = True
except ImportError:
    GeneralNewsExtractor = None
    ListPageExtractor = None
    GNE_AVAILABLE = False
from openai import AsyncOpenAI
from lxml import html as lxml_html
from urllib.parse import urljoin
from app.core.config import settings
import re

logger = logging.getLogger(__name__)

class ParserService:
    """HTML 解析服务"""

    def __init__(self):
        self.llm_client = None
        self._current_llm_config = {}

    def _get_llm_client(self) -> Optional[AsyncOpenAI]:
        """获取或初始化 LLM 客户端，支持动态配置更新"""
        if not settings.llm_api_key:
            return None
        
        # 检查配置是否发生变化
        if (not self.llm_client or 
            self._current_llm_config.get("api_key") != settings.llm_api_key or 
            self._current_llm_config.get("api_base") != settings.llm_api_base):
            
            logger.info("Initializing/Updating LLM client with new configuration")
            self.llm_client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_api_base
            )
            self._current_llm_config = {
                "api_key": settings.llm_api_key,
                "api_base": settings.llm_api_base
            }
            
        return self.llm_client

    async def parse(self, html: str, parser_type: str, config: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        解析 HTML 内容

        Args:
            html: HTML 字符串
            parser_type: 解析器类型 ('gne' 或 'llm' 或 'xpath')
            config: 解析配置
            base_url: 基础 URL，用于拼接相对链接

        Returns:
            Dict: 解析后的结构化数据
        """
        if not html:
            return {"error": "Empty HTML content"}

        if parser_type == "gne":
            return self._parse_with_gne(html, config)
        elif parser_type == "llm":
            return await self._parse_with_llm(html, config)
        elif parser_type == "xpath":
            return self._parse_with_xpath(html, config, base_url)
        else:
            return {"error": f"Unsupported parser type: {parser_type}"}

    def _parse_with_gne(self, html: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用 GNE 解析网页"""
        if not GNE_AVAILABLE:
            logger.warning("GNE is not installed, skipping extraction")
            return {"error": "GNE is not installed on this node. Please install it or use XPath/LLM parser."}
        try:
            config = config or {}
            
            if config.get("mode") == "list":
                if not ListPageExtractor:
                    return {"error": "ListPageExtractor not available in GNE"}
                extractor = ListPageExtractor()
                # 列表模式需要传递 feature 参数，这里使用用户配置的 list_xpath
                feature = config.get("list_xpath") or ""
                return extractor.extract(html, feature)
            
            extractor = GeneralNewsExtractor()
            return extractor.extract(html)
        except Exception as e:
            logger.error(f"GNE extraction failed: {e}")
            return {"error": f"GNE extraction failed: {str(e)}"}

    def _parse_with_xpath(self, html: str, config: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """使用 XPath 解析网页"""
        if not config or not config.get("rules"):
            return {"error": "XPath rules not configured"}

        rules = config.get("rules", {})
        try:
            tree = lxml_html.fromstring(html)
            result = {}
            for field, xpath_expr in rules.items():
                try:
                    # 执行 XPath
                    elements = tree.xpath(xpath_expr)
                    
                    # 处理结果
                    if not elements:
                        result[field] = None
                    elif isinstance(elements, list):
                        # 如果是多个元素，提取文本并合并
                        texts = []
                        for el in elements:
                            val = ""
                            if isinstance(el, str):
                                val = el.strip()
                            else:
                                val = el.text_content().strip()
                            
                            # 如果字段名包含 link/url/image/src/href 且有 base_url，尝试拼接
                            if base_url and any(k in field.lower() for k in ["link", "url", "image", "src", "href"]) and val and not val.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                                val = urljoin(base_url, val)
                                
                            texts.append(val)
                        result[field] = " ".join(filter(None, texts))
                    else:
                        # 单个结果
                        val = ""
                        if isinstance(elements, str):
                            val = elements.strip()
                        else:
                            val = elements.text_content().strip()
                        
                        # 如果字段名包含 link/url/image/src/href 且有 base_url，尝试拼接
                        if base_url and any(k in field.lower() for k in ["link", "url", "image", "src", "href"]) and val and not val.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                            val = urljoin(base_url, val)
                            
                        result[field] = val
                except Exception as e:
                    logger.warning(f"XPath extraction failed for field {field}: {e}")
                    result[field] = f"Error: {str(e)}"
            
            return result
        except Exception as e:
            logger.error(f"XPath parsing failed: {e}")
            return {"error": f"XPath parsing failed: {str(e)}"}

    async def _parse_with_llm(self, html: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用大模型解析网页"""
        llm_client = self._get_llm_client()
        if not llm_client:
            return {"error": "LLM API key not configured"}

        # 检查是否是 XPath 助手模式
        if config and config.get("mode") == "xpath_helper":
            return await self._get_xpath_with_llm(html)

        # 提取需要解析的字段
        fields = config.get("fields", ["title", "content"]) if config else ["title", "content"]
        
        # 简化 HTML 以节省 Token (移除脚本、样式等)
        # 这里做一个简单的预处理，实际应用中可能需要更复杂的清洗
        clean_html = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)
        clean_html = re.sub(r'<.*?>', ' ', clean_html) # 简单粗暴转为文本，或者保留部分结构
        clean_html = " ".join(clean_html.split())[:10000] # 截断以防超出 context window

        prompt = f"""
请从以下 HTML 文本中提取信息，并以 JSON 格式返回。
需要提取的字段包括: {', '.join(fields)}

HTML 文本:
{clean_html}

请只返回合法的 JSON 对象，不要包含任何其他说明文字。
"""
        try:
            response = await llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的网页数据提取助手，擅长从 HTML 中提取结构化信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"error": f"LLM extraction failed: {str(e)}"}

    async def _get_xpath_with_llm(self, html: str) -> Dict[str, Any]:
        """使用大模型分析 HTML 结构并返回 XPath 建议"""
        llm_client = self._get_llm_client()
        
        # 简化 HTML，保留结构但移除大量内容以节省 Token
        # 仅保留具有 class 或 id 的标签，或者 a 标签
        # 使用 BeautifulSoup 会更优雅，但这里先用正则表达式做简单处理
        clean_html = re.sub(r'<(script|style|svg|path|meta|link).*?>.*?</\1>', '', html, flags=re.DOTALL)
        # 移除大部分文本内容，只保留标签结构和关键属性
        lines = []
        for line in clean_html.split('\n'):
            line = line.strip()
            if not line: continue
            # 简化标签，只保留 id 和 class 属性
            line = re.sub(r'<(\w+)\s+[^>]*?(id|class)=["\']([^"\']+)["\'][^>]*>', r'<\1 \2="\3">', line)
            # 移除没有 id/class 的其他属性
            line = re.sub(r'<(\w+)\s+[^>]+>', r'<\1>', line)
            lines.append(line)
        
        struct_html = "\n".join(lines)[:15000] # 截断

        prompt = f"""
你是一个专业的网页解析专家。请分析以下 HTML 结构，并为列表页提取提供最精准的 XPath 规则。
你需要识别页面中的列表容器，以及列表项内部的标题、链接和时间。

HTML 结构片段:
{struct_html}

请返回一个 JSON 对象，包含以下字段：
1. list_xpath: 能够匹配所有列表项容器的 XPath（通常是重复的 div, li, tr 等）
2. title_xpath: 相对于列表项容器的标题提取 XPath（通常是 .//a 或 .//h2 等）
3. link_xpath: 相对于列表项容器的链接提取 XPath（通常是 .//a/@href）
4. time_xpath: 相对于列表项容器的时间提取 XPath（可选，如果能识别到）

请只返回合法的 JSON 对象。
"""
        try:
            response = await llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个网页 XPath 专家，能够精准识别 HTML 结构并生成 XPath。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM XPath generation failed: {e}")
            return {"error": f"LLM XPath generation failed: {str(e)}"}

# 全局解析服务实例
parser_service = ParserService()
