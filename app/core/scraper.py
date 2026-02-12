"""
网页抓取核心模块

使用 Playwright 进行网页渲染和抓取
"""
import time
import base64
import re
import json
import asyncio
import logging
import sys
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from lxml import html as lxml_html
from lxml import etree as lxml_etree

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from app.core.browser import browser_manager
from app.core.drission_browser import drission_manager
from app.core.config import settings
from app.services.proxy_service import proxy_service

logger = logging.getLogger(__name__)


class Scraper:
    """网页抓取器"""

    @staticmethod
    def validate_xpath(xpath: str) -> Optional[str]:
        """校验 XPath 语法是否正确 (仅作为警告日志，不阻塞执行)"""
        if not xpath:
            return None
        try:
            # 尝试预编译 XPath
            lxml_etree.XPath(xpath)
            return None
        except Exception as e:
            # 浏览器引擎 (Playwright/DrissionPage) 对 XPath 的支持通常比 lxml 更宽泛
            # 因此这里仅记录调试日志，不再返回错误字符串给前端拦截
            logger.debug(f"XPath strict validation warning for '{xpath}': {e}")
            return None

    async def scrape_list(
        self,
        url: str,
        list_xpath: str,
        title_xpath: str,
        link_xpath: str,
        time_xpath: Optional[str] = None,
        pagination_next_xpath: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        抓取列表页数据，支持自动翻页（支持链接跳转和点击翻页两种模式）
        """
        params = params or {}
        max_pages = params.get("max_pages", 1)
        next_xpath = pagination_next_xpath or params.get("pagination_next_xpath")
        
        # 如果 max_pages > 1 且有 next_xpath，尝试进入“会话模式”抓取，以支持点击翻页
        if max_pages > 1 and next_xpath:
            return await self._scrape_list_session(
                url, list_xpath, title_xpath, link_xpath, time_xpath, next_xpath, params
            )
            
        # 否则回退到原有的单页/跳转模式
        return await self._scrape_list_legacy(
            url, list_xpath, title_xpath, link_xpath, time_xpath, next_xpath, params
        )

    async def _scrape_list_session(
        self,
        url: str,
        list_xpath: str,
        title_xpath: str,
        link_xpath: str,
        time_xpath: Optional[str],
        next_xpath: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用持久化浏览器会话抓取列表，支持点击翻页"""
        max_pages = params.get("max_pages", 1)
        engine = params.get("engine") or settings.browser_engine
        
        # 目前仅在 Playwright 下实现点击翻页会话模式，DrissionPage 暂维持原样
        if engine == "drissionpage":
            return await self._scrape_list_legacy(
                url, list_xpath, title_xpath, link_xpath, time_xpath, next_xpath, params
            )

        # Windows 兼容性处理：如果不是 Proactor 循环，切换到独立线程
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if sys.platform == 'win32' and loop and type(loop).__name__ != 'ProactorEventLoop':
            return await asyncio.to_thread(
                self._sync_scrape_list_session, 
                url, list_xpath, title_xpath, link_xpath, time_xpath, next_xpath, params
            )
            
        return await self._scrape_list_session_internal(
            url, list_xpath, title_xpath, link_xpath, time_xpath, next_xpath, params
        )

    def _sync_scrape_list_session(self, *args) -> Dict[str, Any]:
        """同步包装器，用于在独立线程中运行异步会话抓取"""
        return asyncio.run(self._scrape_list_session_internal(*args))

    async def _scrape_list_session_internal(
        self,
        url: str,
        list_xpath: str,
        title_xpath: str,
        link_xpath: str,
        time_xpath: Optional[str],
        next_xpath: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Playwright 内部实现：支持点击翻页的会话抓取"""
        max_pages = params.get("max_pages", 1)
        all_items = []
        last_html = ""
        
        page = None
        context = None
        
        try:
            # 处理代理配置
            proxy_config = params.get("proxy")
            proxy_pool_group = params.get("proxy_pool_group")
            
            # 如果配置了代理池，从池中获取随机代理
            if not proxy_config and proxy_pool_group:
                pool_proxy = await proxy_service.get_random_proxy(proxy_pool_group)
                if pool_proxy:
                    proxy_config = {
                        "server": pool_proxy.server,
                        "username": pool_proxy.username,
                        "password": pool_proxy.password
                    }
                    logger.info(f"Using proxy from pool group '{proxy_pool_group}': {pool_proxy.server}")
                else:
                    logger.warning(f"No available proxy in pool group '{proxy_pool_group}', proceeding without proxy")

            browser = await browser_manager.get_browser()
            user_agent = params.get("user_agent") or settings.user_agent
            
            # 创建浏览器上下文参数
            context_options = {
                "java_script_enabled": True,
                "user_agent": user_agent
            }
            
            if proxy_config:
                context_options["proxy"] = {
                    "server": proxy_config.get("server"),
                }
                # 添加代理认证
                if proxy_config.get("username"):
                    context_options["proxy"]["username"] = proxy_config["username"]
                if proxy_config.get("password"):
                    context_options["proxy"]["password"] = proxy_config["password"]

            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            # 设置反检测
            if params.get("stealth", settings.stealth_mode):
                await Stealth().apply_stealth_async(page)
                
            timeout = params.get("timeout", settings.default_timeout)
            wait_for = params.get("wait_for", settings.default_wait_for)
            wait_time = params.get("wait_time", 3000)

            # 初始导航
            logger.info(f"Session scraping started: {url}")
            await page.goto(url, wait_until=wait_for, timeout=timeout)
            if wait_time > 0:
                await page.wait_for_timeout(wait_time)

            for page_num in range(1, max_pages + 1):
                logger.info(f"Scraping page {page_num} in session...")
                
                # 获取当前页面 HTML
                html_content = await page.content()
                last_html = html_content
                tree = lxml_html.fromstring(html_content)
                
                # 提取列表项
                containers = tree.xpath(list_xpath)
                page_items = []
                for container in containers:
                    item = {}
                    def extract_one(xpath_str, default=""):
                        if not xpath_str: return default
                        try:
                            res = container.xpath(xpath_str)
                            if not res: return default
                            if isinstance(res, list):
                                texts = [r.strip() if isinstance(r, str) else r.text_content().strip() for r in res]
                                return " ".join(filter(None, texts))
                            return res.strip() if isinstance(res, str) else res.text_content().strip()
                        except: return default

                    item['title'] = extract_one(title_xpath)
                    link = extract_one(link_xpath)
                    item['link'] = urljoin(page.url, link) if link else ""
                    if time_xpath: item['time'] = extract_one(time_xpath)
                    
                    if item.get('title') or item.get('link'):
                        page_items.append(item)
                
                all_items.extend(page_items)
                logger.info(f"Page {page_num} extracted {len(page_items)} items")

                # 如果不是最后一页，尝试翻页
                if page_num < max_pages:
                    # 点击模式：直接在页面中查找并点击该 XPath 对应的元素
                    logger.info(f"Attempting to click next page button: {next_xpath}")
                    try:
                        # 将 XPath 转换为 Playwright 选择器格式
                        next_button = page.locator(f"xpath={next_xpath}").first
                        
                        # 确保按钮在视图中并可见
                        if await next_button.count() > 0:
                            # 滚动到按钮位置，防止被遮挡或不在视口内
                            await next_button.scroll_into_view_if_needed()
                            
                            # 点击翻页
                            await next_button.click()
                            
                            # 点击后等待内容加载
                            # 优先等待网络空闲，然后再等待指定的 wait_time
                            try:
                                await page.wait_for_load_state("networkidle", timeout=5000)
                            except:
                                pass
                                
                            if wait_time > 0:
                                await page.wait_for_timeout(wait_time)
                                
                            logger.info(f"Clicked next page button, waiting for content...")
                        else:
                            logger.warning(f"Next button not found with XPath: {next_xpath}")
                            break
                    except Exception as e:
                        logger.error(f"Click pagination failed: {e}")
                        break
                else:
                    break

            return {
                "status": "success",
                "html": last_html,
                "items": all_items,
                "count": len(all_items)
            }

        except Exception as e:
            logger.error(f"Session scrape failed: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            if context: await context.close()

    async def _scrape_list_legacy(
        self,
        url: str,
        list_xpath: str,
        title_xpath: str,
        link_xpath: str,
        time_xpath: Optional[str] = None,
        pagination_next_xpath: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        抓取列表页数据，支持自动翻页
        
        Args:
            url: 列表页 URL
            list_xpath: 列表项容器 XPath
            title_xpath: 标题 XPath (相对于列表项)
            link_xpath: 链接 XPath (相对于列表项)
            time_xpath: 时间 XPath (相对于列表项)
            pagination_next_xpath: 下一页按钮 XPath
            params: 抓取参数 (engine, timeout, wait_for_selector, max_pages, pagination_next_xpath 等)
            
        Returns:
            Dict: 包含 items 列表和 html 内容的结果
        """
        params = params or {}
        max_pages = params.get("max_pages", 1)
        next_xpath = pagination_next_xpath or params.get("pagination_next_xpath")
        
        all_items = []
        current_url = url
        last_html = ""
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"Scraping list page {page_num}: {current_url}")
            
            # 1. 获取页面内容
            html_content = ""
            engine = params.get("engine") or settings.browser_engine
            
            # 增加重试机制，如果页面没加载出来，多等一会儿
            max_retries = params.get("max_retries", 2)
            for retry in range(max_retries + 1):
                if engine == "drissionpage":
                    html_content = await self.validate_rules_with_drission(
                        url=current_url,
                        wait_for_selector=params.get("wait_for_selector"),
                        timeout=int((params.get("wait_timeout") or 30000) / 1000),
                        no_images=params.get("no_images", True),
                        no_css=params.get("no_css", True),
                        proxy=params.get("proxy"),
                        proxy_pool_group=params.get("proxy_pool_group")
                    )
                else:
                    # 使用 Playwright 抓取
                    scrape_params = params.copy()
                    # 列表页通常不需要解析器
                    scrape_params["parser"] = None
                    # 如果是重试，增加等待时间
                    if retry > 0:
                        scrape_params["wait_time"] = scrape_params.get("wait_time", 3000) + (retry * 2000)
                        logger.info(f"Retry {retry} for page {page_num}, increasing wait_time to {scrape_params['wait_time']}ms")
                    
                    res = await self.scrape(current_url, scrape_params, "internal")
                    if res.get("status") == "success":
                        html_content = res.get("html", "")
                    else:
                        logger.error(f"Page {page_num} scrape failed: {res.get('error')}")
                        if page_num == 1 and retry == max_retries:
                            return {"status": "failed", "error": res.get("error")}
                        continue # 尝试下一次重试

                if html_content:
                    # 检查是否抓到了列表项，如果没有抓到，也可能需要重试
                    try:
                        # 预先清理和修剪 XPath，防止末尾斜杠等导致 lxml 报错
                        if not list_xpath or not list_xpath.strip():
                            logger.error("List XPath is empty or only whitespace")
                            return {"status": "failed", "error": "List XPath cannot be empty"}
                            
                        list_xpath = list_xpath.strip()
                        if list_xpath.endswith('/') and not list_xpath.endswith('//'):
                            list_xpath = list_xpath[:-1]
                        
                        tree = lxml_html.fromstring(html_content)
                        containers = tree.xpath(list_xpath)
                        if containers:
                            break # 抓到内容了，跳出重试循环
                        else:
                            logger.warning(f"Page {page_num} attempt {retry + 1}: No containers found with XPath {list_xpath}")
                    except lxml_etree.XPathEvalError as e:
                        logger.error(f"XPathEvalError for '{list_xpath}': {e}")
                        return {"status": "failed", "error": f"Invalid List XPath: {e}"}
                    except Exception as e:
                        logger.error(f"Error parsing HTML or XPath: {e}")
                        if retry == max_retries:
                            return {"status": "failed", "error": f"XPath Error: {e}"}
                
                if retry < max_retries:
                    await asyncio.sleep(1) # 等待一秒再重试
            
            if not html_content:
                if page_num == 1:
                    return {"status": "failed", "error": "Failed to get HTML content after retries"}
                break
            
            last_html = html_content
            
            # 2. 解析当前页列表项
            try:
                # 重新解析 tree，因为上面可能已经解析过了，或者为了保险起见
                tree = lxml_html.fromstring(html_content)
                
                # 再次清理 XPath
                list_xpath = list_xpath.strip()
                if list_xpath.endswith('/') and not list_xpath.endswith('//'):
                    list_xpath = list_xpath[:-1]
                
                containers = tree.xpath(list_xpath)
                page_items = []
                
                for container in containers:
                    item = {}
                    
                    def extract_one(xpath_str, default=""):
                        if not xpath_str: return default
                        try:
                            res = container.xpath(xpath_str)
                            if not res: return default
                            if isinstance(res, list):
                                texts = []
                                for r in res:
                                    if isinstance(r, str): texts.append(r.strip())
                                    elif hasattr(r, 'text_content'): texts.append(r.text_content().strip())
                                    else: texts.append(str(r))
                                return " ".join(filter(None, texts))
                            if isinstance(res, str): return res.strip()
                            if hasattr(res, 'text_content'): return res.text_content().strip()
                            return str(res).strip()
                        except Exception:
                            return default

                    item['title'] = extract_one(title_xpath)
                    link = extract_one(link_xpath)
                    if link:
                        item['link'] = urljoin(current_url, link)
                    else:
                        item['link'] = ""
                        
                    if time_xpath:
                        item['time'] = extract_one(time_xpath)
                    
                    if item.get('title') or item.get('link'):
                        page_items.append(item)
                
                all_items.extend(page_items)
                logger.info(f"Page {page_num} extracted {len(page_items)} items")
                
                # 3. 检查是否有下一页
                if page_num < max_pages and next_xpath:
                    try:
                        # 如果 XPath 不以 /@href 或 /@src 结尾，且不是直接取属性的表达式，自动补全 /@href
                        # 这样可以兼容用户只写 a 标签 XPath 的情况
                        check_xpath = next_xpath.strip()
                        if not any(check_xpath.endswith(suffix) for suffix in ['/@href', '/@src', '/text()']) and '[' not in check_xpath.split('/')[-1]:
                            # 尝试先用原 XPath 找，如果没找到 href 属性，再尝试补全
                            next_links = tree.xpath(next_xpath)
                            if next_links and hasattr(next_links[0], 'get') and not next_links[0].get('href'):
                                # 如果找到了元素但没 href，可能需要补全或者已经在属性里了（下面会处理）
                                pass
                        
                        next_links = tree.xpath(next_xpath)
                        
                        # 如果没找到下一页链接，尝试增加等待时间重扫一次当前页（可能分页加载较慢）
                        if not next_links:
                            logger.warning(f"Page {page_num}: Next link not found, retrying with longer wait...")
                            scrape_params = params.copy()
                            scrape_params["parser"] = None
                            scrape_params["wait_time"] = scrape_params.get("wait_time", 3000) + 5000
                            res = await self.scrape(current_url, scrape_params, "internal")
                            if res.get("status") == "success":
                                html_content = res.get("html", "")
                                tree = lxml_html.fromstring(html_content)
                                next_links = tree.xpath(next_xpath)
                    except lxml_etree.XPathEvalError as e:
                        logger.error(f"Invalid Next Page XPath: {e}")
                        break # Skip pagination if XPath is invalid
                    
                    logger.debug(f"Page {page_num} next_links found: {len(next_links)}")
                    if next_links:
                        # 提取链接属性，可能是 href 属性或文本
                        next_url = ""
                        r = next_links[0]
                        if isinstance(r, str):
                            next_url = r.strip()
                        elif hasattr(r, 'get'):
                            # 优先尝试从 a 标签获取 href
                            next_url = r.get('href', '') or r.get('src', '')
                            # 如果还是没有，且有子元素，尝试从子元素获取
                            if not next_url and hasattr(r, 'xpath'):
                                sub_hrefs = r.xpath('.//a/@href')
                                if sub_hrefs:
                                    next_url = sub_hrefs[0]
                        elif hasattr(r, 'text_content'):
                            # 如果是一个 a 标签但没拿到 href，尝试从属性中获取或取文本
                            next_url = r.get('href', '') if hasattr(r, 'get') else ''
                            if not next_url:
                                next_url = r.text_content().strip()
                        
                        logger.info(f"Page {page_num} next_url extracted: {next_url}")
                        if next_url and not next_url.startswith('javascript:'):
                            # 过滤掉常见的非 URL 文本，比如“下一页”文字本身（如果 XPath 指向了文本节点）
                            if not (next_url.startswith('http') or '/' in next_url or '.' in next_url):
                                logger.warning(f"Extracted next_url '{next_url}' seems to be text, not a link. Check your XPath.")
                                # 如果是纯文本且不是相对路径，尝试看原元素是否有 href
                                if hasattr(r, 'get'):
                                    actual_href = r.get('href')
                                    if actual_href:
                                        next_url = actual_href
                            
                            current_url = urljoin(current_url, next_url)
                        else:
                            logger.info(f"Page {page_num}: No valid next page URL found or it is javascript.")
                            break
                    else:
                        logger.info(f"Page {page_num}: No next page link found with XPath: {next_xpath}")
                        break
                else:
                    if page_num >= max_pages:
                        logger.info(f"Reached max pages: {max_pages}")
                    break
                    
            except Exception as e:
                logger.error(f"Failed to parse list at page {page_num}: {e}")
                if page_num == 1:
                    return {"status": "failed", "error": f"Parse error: {str(e)}"}
                break
                
        return {
            "status": "success",
            "html": last_html,
            "items": all_items,
            "count": len(all_items)
        }

    async def scrape(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """
        抓取网页内容，支持 Playwright 和 DrissionPage 引擎
        """
        engine = params.get("engine") or settings.browser_engine
        
        if engine == "drissionpage":
            # 检查代理设置，DrissionPage 目前对带账密的代理支持有限（单例模式下难以动态切换）
            proxy_config = params.get("proxy")
            if proxy_config and (proxy_config.get("username") or proxy_config.get("password")):
                logger.warning("DrissionPage engine currently has limited support for authenticated proxies in singleton mode. Reverting to Playwright or proceed without authentication if it fails.")
            
            return await self._scrape_with_drission(url, params, node_id)
        else:
            return await self._scrape_with_playwright(url, params, node_id)

    async def _scrape_with_playwright(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """
        使用 Playwright 抓取网页 (带 Windows 兼容性处理)
        """
        # 在 Windows 平台上，Playwright 启动子进程需要 ProactorEventLoop
        # 如果当前事件循环不是 ProactorEventLoop (例如是 SelectorEventLoop)，则在独立线程中运行
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if sys.platform == 'win32' and loop and type(loop).__name__ != 'ProactorEventLoop':
            logger.warning(f"当前事件循环为 {type(loop).__name__}，Playwright 在 Windows 上需要 ProactorEventLoop。"
                           f"正在切换到独立线程执行抓取任务以确保兼容性。")
            # 使用 asyncio.to_thread 在新线程中运行，新线程将使用 asyncio.run 开启独立的 Proactor 循环
            return await asyncio.to_thread(self._sync_scrape_with_playwright, url, params, node_id)
        
        return await self._scrape_with_playwright_internal(url, params, node_id)

    def _sync_scrape_with_playwright(self, url: str, params: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """同步包装器，用于在独立线程中运行异步抓取"""
        # asyncio.run 会在当前线程创建一个新的事件循环
        # 由于 app/__init__.py 或 app/main.py 已经设置了 WindowsProactorEventLoopPolicy
        # 这里的 asyncio.run 会自动创建 ProactorEventLoop
        return asyncio.run(self._scrape_with_playwright_internal(url, params, node_id))

    async def _scrape_with_playwright_internal(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """使用 Playwright 抓取网页的内部核心实现"""
        start_time = time.time()
        page = None
        context = None
        intercepted_data = {}  # 存储拦截到的接口数据

        logger.info(f"Scraping with Playwright: {url}")

        try:
            # 获取 User-Agent
            user_agent = params.get("user_agent") or settings.user_agent
            
            # 处理代理配置
            proxy_config = params.get("proxy")
            proxy_pool_group = params.get("proxy_pool_group")
            pool_proxy_id = None
            
            # 如果配置了代理池，从池中获取随机代理
            if not proxy_config and proxy_pool_group:
                pool_proxy = await proxy_service.get_random_proxy(proxy_pool_group)
                if pool_proxy:
                    pool_proxy_id = pool_proxy.id
                    proxy_config = {
                        "server": pool_proxy.server,
                        "username": pool_proxy.username,
                        "password": pool_proxy.password
                    }
                    logger.info(f"Using proxy from pool group '{proxy_pool_group}': {pool_proxy.server}")
                else:
                    logger.warning(f"No available proxy in pool group '{proxy_pool_group}', proceeding without proxy")

            browser = await browser_manager.get_browser()

            # 创建浏览器上下文参数
            context_options = {
                "java_script_enabled": True,
                "user_agent": user_agent
            }
            
            if proxy_config:
                context_options["proxy"] = {
                    "server": proxy_config.get("server"),
                }
                # 添加代理认证
                if proxy_config.get("username"):
                    context_options["proxy"]["username"] = proxy_config["username"]
                if proxy_config.get("password"):
                    context_options["proxy"]["password"] = proxy_config["password"]

            # 创建新的上下文（确保 User-Agent 和 代理设置生效）
            context = await browser.new_context(**context_options)

            # 设置 Cookies
            cookies = params.get("cookies")
            if cookies:
                try:
                    formatted_cookies = []
                    
                    # 提取主域名 (e.g. i.csdn.net -> .csdn.net)
                    # 这样 Cookie 可以在所有子域名（如 api.csdn.net）下共享
                    parsed_url = urlparse(url)
                    host = parsed_url.netloc.split(':')[0]
                    domain_parts = host.split('.')
                    if len(domain_parts) >= 2:
                        main_domain = f".{'.'.join(domain_parts[-2:])}"
                    else:
                        main_domain = host

                    if isinstance(cookies, str):
                        # 处理字符串格式: "name1=value1; name2=value2"
                        for item in cookies.split(';'):
                            item = item.strip()
                            if not item:
                                continue
                            if '=' in item:
                                name, value = item.split('=', 1)
                                cookie_base = {
                                    "name": name.strip(),
                                    "value": value.strip(),
                                    "path": "/",
                                    "secure": parsed_url.scheme == "https",
                                    "sameSite": "Lax"
                                }
                                # 策略：同时在主域名和当前主机名设置 Cookie，确保跨域和主域都能识别
                                formatted_cookies.append({**cookie_base, "domain": main_domain})
                                if host != main_domain.lstrip('.'):
                                    formatted_cookies.append({**cookie_base, "domain": host})
                    elif isinstance(cookies, list):
                        # 处理 JSON 数组格式
                        for cookie in cookies:
                            if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                                # 确保有 domain 或 url
                                if "domain" not in cookie and "url" not in cookie:
                                    cookie["domain"] = main_domain
                                if "path" not in cookie:
                                    cookie["path"] = "/"
                                if "secure" not in cookie:
                                    cookie["secure"] = parsed_url.scheme == "https"
                                formatted_cookies.append(cookie)
                    elif isinstance(cookies, dict):
                        # 处理 JSON 对象格式: {"name1": "value1", "name2": "value2"}
                        for name, value in cookies.items():
                            cookie_base = {
                                "name": name,
                                "value": str(value),
                                "path": "/",
                                "secure": parsed_url.scheme == "https",
                                "sameSite": "Lax"
                            }
                            formatted_cookies.append({**cookie_base, "domain": main_domain})
                            if host != main_domain.lstrip('.'):
                                formatted_cookies.append({**cookie_base, "domain": host})
                    
                    if formatted_cookies:
                        logger.info(f"Adding {len(formatted_cookies)} cookies to context with domain {main_domain}")
                        await context.add_cookies(formatted_cookies)
                except Exception as e:
                    logger.error(f"Error setting cookies: {e}")

            page = await context.new_page()

            # 设置视口大小
            if params.get("viewport"):
                await page.set_viewport_size(params["viewport"])

            # 注入反检测脚本
            if params.get("stealth", settings.stealth_mode):
                await Stealth().apply_stealth_async(page)

            # 设置接口拦截
            intercept_apis = params.get("intercept_apis", [])
            if intercept_apis:
                intercept_continue = params.get("intercept_continue", False)
                await self._setup_api_interception(
                    page, 
                    intercept_apis, 
                    intercepted_data, 
                    intercept_continue
                )

            # 拦截资源（图片、媒体等）
            if params.get("block_images", settings.block_images) or params.get("block_media", settings.block_media):
                await self._block_resources(page, params)

            # 获取等待策略和超时设置
            wait_for = params.get("wait_for", settings.default_wait_for)
            wait_time = params.get("wait_time", 3000)
            timeout = params.get("timeout", settings.default_timeout)

            # 导航到目标 URL
            response = None
            try:
                response = await page.goto(
                    url,
                    wait_until=wait_for,
                    timeout=timeout
                )
            except PlaywrightTimeoutError:
                # 超时容错：如果已经有响应或页面有内容，则继续
                if not page.is_closed():
                    html_preview = await page.content()
                    if len(html_preview) > 200: # 认为页面已经加载了部分内容
                        pass
                    else:
                        raise # 页面内容太少，还是抛出超时异常

            # 等待特定选择器
            if params.get("selector"):
                try:
                    await page.wait_for_selector(params["selector"], timeout=timeout)
                except PlaywrightTimeoutError:
                    # 如果已经有内容，选择器超时也可以容忍
                    pass

            # 额外等待时间
            if wait_time > 0:
                await page.wait_for_timeout(wait_time)

            # 获取页面 HTML
            html = await page.content()
            actual_url = page.url # 获取重定向后的实际 URL

            # 计算加载时间
            load_time = time.time() - start_time

            # 获取页面标题和状态码
            title = ""
            status_code = 0
            try:
                title = await page.title()
                if response:
                    status_code = response.status
                else:
                    # 如果 response 为空（超时），尝试从 main_frame 获取
                    status_code = 200 # 默认为 200，因为我们能拿到内容
            except:
                pass

            # 可选：截图
            screenshot = None
            if params.get("screenshot"):
                try:
                    # 使用 is_fullscreen 参数控制是否全页截图，默认 False
                    is_fullscreen = params.get("is_fullscreen", False)
                    screenshot_bytes = await page.screenshot(full_page=is_fullscreen)
                    screenshot = base64.b64encode(screenshot_bytes).decode()
                except:
                    pass

            # 返回成功结果
            result = {
                "status": "success",
                "html": html,
                "screenshot": screenshot,
                "metadata": {
                    "title": title,
                    "url": url,
                    "actual_url": actual_url,
                    "status_code": status_code,
                    "load_time": load_time,
                    "timestamp": time.time(),
                    "proxy": proxy_config.get("server") if proxy_config else None
                }
            }

            # 如果有拦截的接口数据，添加到结果中
            if intercepted_data:
                result["intercepted_apis"] = intercepted_data

            # 更新代理统计
            if pool_proxy_id:
                await proxy_service.update_stats(pool_proxy_id, success=True)

            return result

        except Exception as e:
            # 返回失败结果
            load_time = time.time() - start_time
            
            # 更新代理统计
            if pool_proxy_id:
                await proxy_service.update_stats(pool_proxy_id, success=False)

            error_result = {
                "status": "failed",
                "error": {
                    "message": str(e),
                    "type": type(e).__name__
                },
                "metadata": {
                    "url": url,
                    "load_time": load_time,
                    "timestamp": time.time()
                }
            }

            # 如果有拦截的接口数据，也添加到错误结果中
            if intercepted_data:
                error_result["intercepted_apis"] = intercepted_data

            return error_result

        finally:
            # 确保关闭页面和上下文
            try:
                if page and context:
                    # 关闭上下文（会自动关闭页面）
                    await context.close()
                elif page:
                    # 只关闭页面
                    await page.close()
            except Exception as e:
                # 忽略关闭时的错误，通常是因为浏览器已经关闭
                logger.debug(f"Error closing playwright resources: {e}")

    async def _scrape_with_drission(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """使用 DrissionPage 抓取网页，通过 asyncio.to_thread 运行同步代码"""
        # 处理代理池配置
        proxy_pool_group = params.get("proxy_pool_group")
        pool_proxy_id = None
        if not params.get("proxy") and proxy_pool_group:
            pool_proxy = await proxy_service.get_random_proxy(proxy_pool_group)
            if pool_proxy:
                pool_proxy_id = pool_proxy.id
                params["proxy"] = {
                    "server": pool_proxy.server,
                    "username": pool_proxy.username,
                    "password": pool_proxy.password
                }
                logger.info(f"Using proxy from pool group '{proxy_pool_group}' for DrissionPage: {pool_proxy.server}")
        
        result = await asyncio.to_thread(self._sync_scrape_with_drission, url, params, node_id)
        
        # 更新代理统计
        if pool_proxy_id:
            success = result.get("status") == "success"
            await proxy_service.update_stats(pool_proxy_id, success=success)
            
        return result

    def _sync_scrape_with_drission(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """DrissionPage 的同步抓取实现 (单例模式)"""
        start_time = time.time()
        logger.info(f"Scraping with DrissionPage (singleton): {url}")
        
        # 使用线程安全的方法创建标签页，并自动更新最后使用时间
        tab = None
        try:
            # 设置超时 (DrissionPage 默认 10s)
            timeout_ms = params.get("timeout", settings.default_timeout)
            timeout_s = timeout_ms / 1000

            # 创建一个新标签页，支持资源拦截配置
            tab = drission_manager.create_tab(
                no_images=params.get("no_images", False),
                no_css=params.get("no_css", False),
                proxy=params.get("proxy"),
                proxy_pool_group=params.get("proxy_pool_group")
            )
            
            # 在新标签页中访问 URL，并设置超时
            tab.get(url, timeout=timeout_s)
            
            # 处理 Cloudflare 挑战
            # 循环检查是否还在挑战页面，最多等待 60 秒
            wait_start = time.time()
            max_wait = 60
            
            logger.info(f"Waiting for Cloudflare challenge (max {max_wait}s)...")
            while time.time() - wait_start < max_wait:
                html_lower = tab.html.lower()
                title = tab.title
                
                # 如果标题不再是 "请稍候" 或 "checking your browser" 等，说明可能通过了
                if "checking your browser" not in html_lower and \
                   "just a moment" not in html_lower and \
                   "请稍候" not in title and \
                   "验证您是否是真人" not in title:
                    logger.info("Cloudflare challenge seems bypassed.")
                    break
                
                # 直接获取div, 点击
                try:
                    tab.ele("x://div[@class='main-content']/div[1]").click.at(30, 30)
                    tab.ele("x://div[@class='main-content']/div[1]").click.at(40, 40)
                except Exception as e:
                    # 忽略查找过程中的小错误
                    pass
                    
                time.sleep(5)
            else:
                logger.warning("Cloudflare challenge wait timeout.")
            
            # 等待特定元素 (如果指定)
            selector = params.get("selector")
            if selector:
                try:
                    tab.ele(selector, timeout=timeout_s)
                except:
                    logger.warning(f"Selector {selector} not found within timeout")
            
            # 获取内容
            # 即使 save_html 为 False，如果需要解析 (parser 不为空)，也需要获取 HTML
            html = tab.html if params.get("save_html", True) or params.get("parser") else ""
            title = tab.title
            actual_url = tab.url
            
            # 截图
            screenshot = None
            if params.get("screenshot"):
                try:
                    is_fullscreen = params.get("is_fullscreen", False)
                    screenshot_bytes = tab.get_screenshot(full_page=is_fullscreen, as_bytes=True)
                    screenshot = base64.b64encode(screenshot_bytes).decode()
                except Exception as e:
                    logger.error(f"Error taking screenshot with DrissionPage: {e}")

            load_time = time.time() - start_time
            
            return {
                "status": "success",
                "html": html,
                "screenshot": screenshot,
                "metadata": {
                    "title": title,
                    "url": url,
                    "actual_url": actual_url,
                    "status_code": 200, 
                    "load_time": load_time,
                    "timestamp": time.time(),
                    "engine": "drissionpage",
                    "proxy": params.get("proxy", {}).get("server") if params.get("proxy") else None
                }
            }
        except Exception as e:
            logger.error(f"DrissionPage scrape failed: {e}")
            return {
                "status": "failed",
                "error": {"message": str(e), "type": type(e).__name__},
                "metadata": {
                    "url": url,
                    "load_time": time.time() - start_time,
                    "timestamp": time.time(),
                    "engine": "drissionpage"
                }
            }
        finally:
            if tab:
                try:
                    # 抓取完成后关闭该标签页，但不关闭整个浏览器
                    tab.close()
                except:
                    pass

    async def validate_rules_with_drission(
        self,
        url: str,
        wait_for_selector: str = None,
        timeout: int = 30,
        no_images: bool = False,
        no_css: bool = False,
        proxy: dict = None,
        proxy_pool_group: str = None
    ) -> str:
        """
        使用 DrissionPage 验证抓取规则 (获取渲染后的 HTML)
        独立函数，确保资源正确管理和冲突处理
        """
        # 如果提供了代理池但没提供具体代理，先异步获取一个代理
        if not proxy and proxy_pool_group:
            pool_proxy = await proxy_service.get_random_proxy(proxy_pool_group)
            if pool_proxy:
                proxy = {
                    "server": pool_proxy.server,
                    "username": pool_proxy.username,
                    "password": pool_proxy.password
                }
                logger.info(f"Using proxy from pool group '{proxy_pool_group}' for DrissionPage validation: {pool_proxy.server}")

        return await asyncio.to_thread(
            self._sync_validate_with_drission,
            url,
            wait_for_selector,
            timeout,
            no_images,
            no_css,
            proxy,
            proxy_pool_group
        )

    def _sync_validate_with_drission(
        self,
        url: str,
        wait_for_selector: str = None,
        timeout: int = 30,
        no_images: bool = False,
        no_css: bool = False,
        proxy: dict = None,
        proxy_pool_group: str = None
    ) -> str:
        """同步执行 DrissionPage 验证"""
        tab = None
        try:
            # 使用线程安全的方法创建标签页
            tab = drission_manager.create_tab(
                no_images=no_images, 
                no_css=no_css,
                proxy=proxy,
                proxy_pool_group=proxy_pool_group
            )
            
            # 访问页面
            tab.get(url, timeout=timeout)
            
            # 等待特定元素
            if wait_for_selector:
                try:
                    tab.wait.ele_displayed(wait_for_selector, timeout=timeout)
                except Exception as e:
                    logger.warning(f"Wait for selector {wait_for_selector} timeout: {e}")
            
            # 简单的 Cloudflare 检查
            if "checking your browser" in tab.title.lower() or "just a moment" in tab.title.lower():
                logger.info("Encountered Cloudflare challenge in validation, waiting...")
                time.sleep(5)
            
            return tab.html
            
        except Exception as e:
            logger.error(f"Validation fetch failed: {e}")
            raise e
        finally:
            if tab:
                try:
                    tab.close()
                except Exception as e:
                    logger.warning(f"Error closing validation tab: {e}")

    async def _setup_api_interception(
        self,
        page,
        api_patterns: List[str],
        intercepted_data: Dict[str, Any],
        continue_after_intercept: bool = False
    ):
        """
        设置接口拦截

        Args:
            page: Playwright 页面对象
            api_patterns: 要拦截的接口 URL 模式列表（支持通配符 *）
            intercepted_data: 用于存储拦截数据的字典
            continue_after_intercept: 拦截并获取数据后，是否继续执行后续请求（默认 False）
        """
        def url_matches_pattern(url: str, pattern: str) -> bool:
            """
            检查 URL 是否匹配模式

            Args:
                url: 实际 URL
                pattern: URL 模式（支持通配符 *）

            Returns:
                bool: 是否匹配
            """
            # 转义正则特殊字符，但保留 * 作为通配符
            regex_pattern = re.escape(pattern).replace(r"\*", ".*")
            # 使用 re.search 确保在 URL 任何位置都能匹配，或者在正则前后加 ^ $
            return re.search(f"^{regex_pattern}$", url) is not None

        async def route_handler(route, request):
            """路由处理函数"""
            try:
                # 检查请求 URL 是否匹配任何拦截模式
                request_url = request.url
                matched_pattern = None

                for pattern in api_patterns:
                    if url_matches_pattern(request_url, pattern):
                        matched_pattern = pattern
                        break

                if matched_pattern:
                    # 拦截请求，获取响应
                    try:
                        response = await route.fetch()
                        
                        # 获取响应数据
                        content_type = response.headers.get("content-type", "")
                        
                        # 清理 Headers，防止 MongoDB 键名冲突（键名不能包含 . 或 $）
                        safe_headers = {}
                        for k, v in response.headers.items():
                            safe_k = k.replace(".", "_").replace("$", "_")
                            safe_headers[safe_k] = v

                        response_data = {
                            "url": request_url,
                            "method": request.method,
                            "status": response.status,
                            "headers": safe_headers,
                        }

                        # 尝试获取响应体
                        try:
                            body_bytes = await response.body()
                            logger.info(f"Captured {len(body_bytes)} bytes for {request_url}")
                            if "application/json" in content_type:
                                try:
                                    response_data["body"] = json.loads(body_bytes.decode('utf-8'))
                                except:
                                    response_data["body"] = body_bytes.decode('utf-8', errors='replace')
                            elif any(t in content_type for t in ["text/", "javascript", "xml", "html"]):
                                response_data["body"] = body_bytes.decode('utf-8', errors='replace')
                            else:
                                # 对于二进制数据，使用 base64 编码
                                response_data["body"] = f"data:{content_type};base64," + base64.b64encode(body_bytes).decode('utf-8')
                                response_data["is_binary"] = True
                        except Exception as body_err:
                            response_data["body"] = f"Error capturing body: {str(body_err)}"

                        # 存储拦截数据
                        # MongoDB 不允许键名中包含 "." 或 "$" 符号
                        # 我们对 pattern 进行转义处理，将 "." 替换为 "_"
                        safe_pattern = matched_pattern.replace(".", "_").replace("$", "_")
                        
                        if safe_pattern not in intercepted_data:
                            intercepted_data[safe_pattern] = []
                        intercepted_data[safe_pattern].append(response_data)
                        logger.info(f"Stored intercepted data for {safe_pattern}, body length: {len(str(response_data.get('body', '')))}")

                        # 判断是否继续请求
                        if continue_after_intercept:
                            # 如果已经 fetch 了响应，必须用 fulfill 返回给页面，否则继续请求会导致重复发送
                            await route.fulfill(response=response)
                        else:
                            await route.abort()
                    except Exception as fetch_err:
                        logger.error(f"Error fetching route: {fetch_err}")
                        await route.fallback()
                else:
                    # 不匹配，交给下一个处理器或正常请求
                    await route.fallback()
            except Exception as e:
                # 拦截失败时尝试交给下一个处理器
                logger.error(f"Interception handler error: {e}")
                await route.fallback()

        # 注册路由处理器
        await page.route("**/*", route_handler)

    async def _block_resources(self, page, params: Dict[str, Any]):
        """
        拦截指定类型的资源

        Args:
            page: Playwright 页面对象
            params: 抓取参数
        """
        async def route_handler(route, request):
            """路由处理函数"""
            resource_type = request.resource_type

            # 拦截图片
            if params.get("block_images") and resource_type == "image":
                await route.abort()
            # 拦截媒体资源和字体、css
            elif params.get("block_media") and resource_type in ["media", "font", "stylesheet"]:
                await route.abort()
            # 继续加载其他资源，允许其他路由处理器继续处理
            else:
                await route.fallback()

        # 注册路由处理器
        await page.route("**/*", route_handler)


# 全局抓取器实例
scraper = Scraper()
