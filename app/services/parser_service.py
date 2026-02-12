"""
HTML 解析服务模块

支持基于 gerapy-auto-extractor 和 LLM (Large Language Model) 的网页内容解析
"""
import json
import logging
from typing import Dict, Any, Optional, List
try:
    from gne import GeneralNewsExtractor
    GNE_AVAILABLE = True
except ImportError:
    GeneralNewsExtractor = None
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
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"error": f"LLM extraction failed: {str(e)}"}

    async def generate_xpath_rules(self, html: str) -> Dict[str, str]:
        """使用 LLM 生成 XPath 规则"""
        llm_client = self._get_llm_client()
        if not llm_client:
            return {"error": "LLM API key not configured"}

        # 简化 HTML: 移除 script, style, svg, path 等非结构化标签，保留 div, span, a, ul, li, table 等结构标签
        # 同时保留 class 和 id 属性，这对于 XPath 至关重要
        clean_html = re.sub(r'<(script|style|svg|path|noscript).*?>.*?</\1>', '', html, flags=re.DOTALL)
        clean_html = re.sub(r'<!--.*?-->', '', clean_html, flags=re.DOTALL)
        # 移除过长的文本内容，只保留前 50 个字符，减少 Token 消耗
        clean_html = re.sub(r'>([^<]{50,})<', lambda m: f">{m.group(1)[:20]}...<", clean_html)
        
        # 进一步截断，保留前 15000 个字符 (根据模型上下文窗口调整)
        clean_html = " ".join(clean_html.split())[:100000]

        prompt = f"""
你是一个专业的爬虫工程师。请分析以下 HTML 片段，识别列表页的结构，并生成对应的 XPath 提取规则。
HTML 片段:
{clean_html}

请识别以下字段的 XPath:
1. list_xpath: 列表项的容器（例如 //div[@class='list-item']）。
2. title_xpath: 列表项中的标题（相对于 list_xpath 的相对路径）。
3. link_xpath: 列表项中的详情页链接（相对于 list_xpath 的相对路径）。
4. time_xpath: 发布时间（相对于 list_xpath 的相对路径）。
5. pagination_next_xpath: 下一页按钮的 XPath（绝对路径，指向可点击的翻页按钮，优先使用字符匹配，不限于下一页、下页、>等）。

请注意：
- 对于具有多个类名的元素（例如 <div class="pagination mb20">），**严禁**使用 `@class='pagination'` 这种完全匹配语法，必须使用 `contains(@class, 'pagination')` 这种部分匹配语法。
- 严禁在生成的 XPath 末尾添加多余的斜杠 `/`。
- list_xpath、title_xpath、link_xpath 是必需的。
- pagination_next_xpath 必须是能够定位到“下一页”或者翻页按钮。
- 如果找不到某个字段，value 设为 null。
- 请以 JSON 格式返回，key 为上述字段名，value 为 XPath 字符串。
- 请确保生成的 XPath 尽可能通用且健壮，优先使用 id 或具有语义的 class。
- 只返回 JSON 对象。
"""
        try:
            response = await llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个XPath规则生成专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=60
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM rule generation failed: {e}")
            return {"error": f"Rule generation failed: {str(e)}"}

# 全局解析服务实例
parser_service = ParserService()
