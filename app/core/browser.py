"""
Playwright 浏览器管理模块

提供浏览器实例的单例管理，支持启动浏览器、创建页面等功能
"""
import asyncio
import logging
import sys
import threading
import time
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserType
from app.core.config import settings

logger = logging.getLogger(__name__)

class BrowserManager:
    """浏览器管理单例类"""

    _instance = None  # 单例实例

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._local = threading.local()
        return cls._instance

    @property
    def _playwright(self):
        return getattr(self._local, 'playwright', None)

    @_playwright.setter
    def _playwright(self, value):
        self._local.playwright = value

    @property
    def _browser(self) -> Optional[Browser]:
        return getattr(self._local, 'browser', None)

    @_browser.setter
    def _browser(self, value):
        self._local.browser = value

    @property
    def _last_used_time(self):
        return getattr(self._local, 'last_used_time', 0)

    @_last_used_time.setter
    def _last_used_time(self, value):
        self._local.last_used_time = value

    async def get_playwright(self):
        """
        获取 Playwright 实例，如果不存在则创建

        Returns:
            Playwright: Playwright 实例
        """
        if self._playwright is None:
            # Windows 诊断日志
            if sys.platform == 'win32':
                loop = asyncio.get_running_loop()
                loop_type = type(loop).__name__
                logger.info(f"Starting Playwright. Current loop type: {loop_type}")
                if loop_type != 'ProactorEventLoop':
                    logger.error("CRITICAL: Playwright requires ProactorEventLoop on Windows, but found %s", loop_type)
            
            self._playwright = await async_playwright().start()
        return self._playwright

    def is_browser_connected(self) -> bool:
        """
        检查浏览器是否已连接
        
        Returns:
            bool: 浏览器是否已连接
        """
        browser = getattr(self._local, 'browser', None)
        return browser is not None and browser.is_connected()

    async def get_browser(self) -> Browser:
        """
        获取浏览器实例，如果不存在或未连接则创建

        Returns:
            Browser: 浏览器实例
        """
        if self._browser is None or not self._browser.is_connected():
            playwright = await self.get_playwright()

            # 浏览器类型映射
            browser_type_map = {
                "chromium": playwright.chromium,
                "firefox": playwright.firefox,
                "webkit": playwright.webkit
            }

            # 获取配置的浏览器类型，默认使用 chromium
            browser_type: BrowserType = browser_type_map.get(
                settings.browser_type,
                playwright.chromium
            )

            # 启动浏览器参数
            launch_args = []
            
            # 反检测参数
            if settings.stealth_mode:
                launch_args.extend([
                    "--no-sandbox", 
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage", 
                    "--disable-gpu", 
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ])

            # 启动浏览器
            self._browser = await browser_type.launch(
                headless=settings.headless,
                args=launch_args
            )

        # 更新最后使用时间
        self._last_used_time = time.time()
        return self._browser

    async def new_page(self) -> Page:
        """
        创建新的浏览器页面

        Returns:
            Page: 浏览器页面实例
        """
        browser = await self.get_browser()
        return await browser.new_page()

    async def check_idle_browser(self):
        """
        检查浏览器是否长时间空闲，如果是则关闭浏览器，释放内存
        """
        if self._browser and self._browser.is_connected():
            # 如果还有打开的上下文或页面，可能不应该直接关闭整个浏览器
            # 但为了简单释放内存，这里按照闲置时间逻辑处理
            current_time = time.time()
            idle_time = current_time - self._last_used_time
            
            if idle_time > settings.browser_idle_timeout:
                logger.info(f"Playwright browser idle for {int(idle_time)}s, closing...")
                await self.close_browser()

    async def close_browser(self):
        """关闭浏览器实例"""
        if self._browser:
            logger.info("Closing browser instance")
            await self._browser.close()
            self._browser = None

    async def close_playwright(self):
        """关闭 Playwright 和浏览器实例"""
        logger.info("Closing Playwright instance")
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self._browser = None


# 全局浏览器管理器实例
browser_manager = BrowserManager()
