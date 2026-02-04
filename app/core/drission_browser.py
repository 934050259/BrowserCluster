"""
DrissionPage 浏览器管理模块

提供 ChromiumPage 实例的单例管理，支持浏览器复用和标签页管理
"""
import logging
import threading
import time
from typing import Optional
from DrissionPage import ChromiumPage, ChromiumOptions
from app.core.config import settings
# 设置浏览器可执行文件路径
import shutil
import glob
import os

logger = logging.getLogger(__name__)

class DrissionManager:
    """DrissionPage 浏览器管理单例类"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._page = None
                cls._instance._last_used_time = 0
        return cls._instance

    def get_browser(self, params: dict = None) -> ChromiumPage:
        """
        获取或创建 ChromiumPage 实例 (单例)
        
        Args:
            params: 抓取参数，用于初始化配置
            
        Returns:
            ChromiumPage: 浏览器页面实例
        """
        with self._lock:
            self._last_used_time = time.time()
            
            # 如果实例已存在且未关闭，直接返回
            if self._page:
                try:
                    # 尝试访问一个属性检查是否存活
                    _ = self._page.tabs_count
                    return self._page
                except Exception:
                    logger.info("DrissionPage instance disconnected, recreating...")
                    self._page = None

            # 创建新实例
            logger.info("Initializing new DrissionPage singleton instance...")
            co = ChromiumOptions()
            
            # 基础配置
            if params and params.get("headless", settings.headless):
                co.headless()
            
            # 设置独立的 UserData 目录，避免与 Playwright 冲突
            user_data_path = f"/tmp/drission_user_{os.getpid()}"
            co.set_user_data_path(user_data_path)
            
            # 优先级 1: 环境变量指定路径
            browser_path = os.environ.get('BROWSER_PATH')
            
            # 优先级 2: 系统路径搜索
            if not browser_path:
                browser_path = shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('chrome')
            
            # 优先级 3: 常见的 Playwright 安装路径
            if not browser_path:
                search_paths = [
                    '/ms-playwright/chromium-*/chrome-linux/chrome',
                    '/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome',
                    '/home/pwuser/.cache/ms-playwright/chromium-*/chrome-linux/chrome',
                    '/usr/bin/chromium',
                    '/usr/bin/google-chrome'
                ]
                for pattern in search_paths:
                    matches = glob.glob(pattern)
                    if matches:
                        browser_path = matches[0]
                        break
            
            if browser_path:
                logger.info(f"DrissionPage found browser at: {browser_path}")
                co.set_browser_path(browser_path)
            else:
                logger.error("DrissionPage could not find any browser executable in common locations!")

            # Linux 特定反检测和沙箱配置
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-gpu')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-blink-features=AutomationControlled')
            co.set_argument('--disable-infobars')
            co.set_argument('--lang=zh-CN,zh;q=0.9')
            # 解决 Linux 环境下某些反爬检测
            co.set_argument('--hide-scrollbars')
            co.set_argument('--mute-audio')
            co.set_argument('--no-first-run')
            co.set_argument('--no-default-browser-check')
            co.set_argument('--ignore-certificate-errors')
            # 设置默认窗口大小
            co.set_argument('--window-size=1920,1080')
            # co.incognito() # 无痕模式
            
            # 禁用下载管理器以避免部分环境下的初始化错误 (_dl_mgr 报错)
            co.set_paths(download_path='') 
            
            # 显式指定一个端口，避免默认端口冲突
            # 同时禁用自动查找可用端口，防止 WebSocket 握手失败 (404)
            import socket
            def get_free_port():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', 0))
                    return s.getsockname()[1]
            
            port = get_free_port()
            co.set_address(f'127.0.0.1:{port}')
            
            # 设置默认 User-Agent
            ua = (params.get("user_agent") if params else None) or settings.user_agent
            co.set_user_agent(ua)
            
            self._page = ChromiumPage(co)
            return self._page

    def close_browser(self):
        """关闭浏览器实例"""
        with self._lock:
            if self._page:
                try:
                    self._page.quit()
                    logger.info("DrissionPage instance closed.")
                except Exception as e:
                    logger.error(f"Error closing DrissionPage: {e}")
                finally:
                    self._page = None

    @property
    def is_active(self) -> bool:
        """检查浏览器是否处于激活/打开状态"""
        with self._lock:
            return self._page is not None

    @property
    def last_used_time(self):
        return self._last_used_time

drission_manager = DrissionManager()
