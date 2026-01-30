"""
网页抓取核心模块

使用 Playwright 进行网页渲染和抓取
"""
import time
import base64
import re
import json
from typing import Optional, Dict, Any, List, Union
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from app.core.browser import browser_manager
from app.core.config import settings


class Scraper:
    """网页抓取器"""

    async def scrape(
        self,
        url: str,
        params: Dict[str, Any],
        node_id: str
    ) -> Dict[str, Any]:
        """
        抓取网页内容

        Args:
            url: 目标 URL
            params: 抓取参数
            node_id: 处理节点 ID

        Returns:
            Dict: 包含状态、HTML、元数据等信息的字典
        """
        start_time = time.time()
        page = None
        context = None
        intercepted_data = {}  # 存储拦截到的接口数据

        print(f"Scraping URL: {url} with params: {params}")

        try:
            # 获取 User-Agent
            user_agent = params.get("user_agent") or settings.user_agent
            
            # 处理代理配置
            proxy_config = params.get("proxy")
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
                    if isinstance(cookies, str):
                        # 处理字符串格式: "name1=value1; name2=value2"
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        for item in cookies.split(';'):
                            if '=' in item:
                                name, value = item.strip().split('=', 1)
                                formatted_cookies.append({
                                    "name": name,
                                    "value": value,
                                    "domain": domain,
                                    "path": "/"
                                })
                    elif isinstance(cookies, list):
                        # 处理 JSON 数组格式
                        for cookie in cookies:
                            if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                                # 确保有 domain，Playwright 要求 cookie 必须有 domain 或 url
                                if "domain" not in cookie and "url" not in cookie:
                                    from urllib.parse import urlparse
                                    cookie["domain"] = urlparse(url).netloc
                                formatted_cookies.append(cookie)
                    
                    if formatted_cookies:
                        await context.add_cookies(formatted_cookies)
                except Exception as e:
                    print(f"Error setting cookies: {e}")

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
            if page and context:
                # 关闭上下文（会自动关闭页面）
                await context.close()
            elif page:
                # 只关闭页面
                await page.close()

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
            # 将通配符 * 转换为正则表达式
            regex_pattern = pattern.replace("*", ".*")
            return re.match(regex_pattern, url) is not None

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
                    response = await route.fetch()

                    # 获取响应数据
                    content_type = response.headers.get("content-type", "")
                    response_data = {
                        "url": request_url,
                        "method": request.method,
                        "status": response.status,
                        "headers": dict(response.headers),
                    }

                    # 尝试解析 JSON 响应
                    if "application/json" in content_type:
                        try:
                            json_data = await response.json()
                            response_data["body"] = json_data
                        except:
                            response_data["body"] = await response.text()
                    else:
                        # 非 JSON 响应，存储文本内容
                        response_data["body"] = await response.text()

                    # 存储拦截数据
                    if matched_pattern not in intercepted_data:
                        intercepted_data[matched_pattern] = []
                    intercepted_data[matched_pattern].append(response_data)

                    # 判断是否继续请求
                    if continue_after_intercept:
                        await route.continue_()
                    else:
                        # 不执行后续请求，直接中止（或可以使用 route.fulfill 返回已获取的数据，但 abort 更符合“不执行后续”的描述）
                        await route.abort()
                else:
                    # 不匹配，正常请求
                    await route.continue_()
            except Exception as e:
                # 拦截失败时继续请求
                await route.continue_()

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
            # 继续加载其他资源
            else:
                await route.continue_()

        # 注册路由处理器
        await page.route("**/*", route_handler)


# 全局抓取器实例
scraper = Scraper()
