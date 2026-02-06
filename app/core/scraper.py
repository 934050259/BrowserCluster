"""
网页抓取核心模块

使用 Playwright 进行网页渲染和抓取
"""
import time
import base64
import re
import json
import logging
import asyncio
from typing import Dict, Any, List
from urllib.parse import urlparse

from playwright_stealth import Stealth

from app.core.browser import browser_manager
from app.core.drission_browser import drission_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class Scraper:
    """网页抓取器"""

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
        """使用 Playwright 抓取网页"""
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
            browser = await browser_manager.get_browser()

            # 创建浏览器上下文参数
            context_options = {
                "java_script_enabled": True,
                # "user_agent": user_agent
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
                    "timestamp": time.time()
                }
            }

            # 如果有拦截的接口数据，添加到结果中
            if intercepted_data:
                result["intercepted_apis"] = intercepted_data

            return result

        except Exception as e:
            # 返回失败结果
            load_time = time.time() - start_time
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
        return await asyncio.to_thread(self._sync_scrape_with_drission, url, params, node_id)

    def _sync_scrape_with_drission(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """DrissionPage 的同步抓取实现 (单例模式)"""
        start_time = time.time()
        logger.info(f"Scraping with DrissionPage (singleton): {url}")
        
        # 获取单例浏览器实例
        browser = drission_manager.get_browser(params)
        
        # 创建新标签页
        tab = None
        try:
            # 设置超时 (DrissionPage 默认 10s)
            timeout_ms = params.get("timeout", settings.default_timeout)
            timeout_s = timeout_ms / 1000

            # 创建一个新标签页
            tab = browser.new_tab()
            
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
                    "engine": "drissionpage"
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
