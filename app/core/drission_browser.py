"""
DrissionPage 浏览器管理模块

提供 ChromiumPage 实例的单例管理，支持浏览器复用和标签页管理
"""
import logging
import threading
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from app.core.config import settings
import shutil
import glob
import os
import socket

logger = logging.getLogger(__name__)

class DrissionManager:
    """DrissionPage 浏览器管理单例类"""

    _instance = None
    _lock = threading.RLock()

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
            if params :
                if params.get("headless", settings.headless):
                    co.headless()
            else:
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
            def get_free_port():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', 0))
                    return s.getsockname()[1]
            
            port = get_free_port()
            co.set_address(f'127.0.0.1:{port}')
            
            # 设置默认 User-Agent
            ua = (params.get("user_agent") if params else None) or settings.user_agent
            co.set_user_agent(ua)
            
            # 设置代理
            if params and params.get("proxy"):
                proxy_config = params.get("proxy")
                if isinstance(proxy_config, dict) and proxy_config.get("server"):
                    server = proxy_config["server"]
                    # DrissionPage 代理格式: 'http://user:pass@host:port'
                    if proxy_config.get("username") and proxy_config.get("password"):
                        user = proxy_config["username"]
                        password = proxy_config["password"]
                        if '://' in server:
                            protocol, address = server.split('://', 1)
                            server = f"{protocol}://{user}:{password}@{address}"
                        else:
                            server = f"http://{user}:{password}@{server}"
                    
                    co.set_proxy(server)
                    logger.info(f"DrissionPage initialized with proxy: {server}")
            
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

    def check_idle(self, timeout: int = 300):
        """
        检查并关闭空闲浏览器
        
        Args:
            timeout: 空闲时间超过此秒数则关闭，默认 5 分钟
        """
        with self._lock:
            if not self._page:
                return
                
            current_time = time.time()
            # 如果空闲时间超过阈值
            if self._last_used_time > 0 and (current_time - self._last_used_time) > timeout:
                try:
                    # 检查是否还有除主标签页以外的活动标签页
                    # 如果 tabs_count > 1，说明还有任务在运行（如正在抓取或正在校验）
                    if self._page.tabs_count <= 1:
                        logger.info(f"DrissionPage idle for {int(current_time - self._last_used_time)}s and no active tabs, closing...")
                        self.close_browser()
                    else:
                        # 还有活动标签页，更新时间戳，顺延检查
                        logger.debug(f"DrissionPage has {self._page.tabs_count} active tabs, skipping idle cleanup")
                        self._last_used_time = current_time
                except Exception as e:
                    logger.error(f"Error during DrissionPage idle check: {e}")
                    # 如果发生异常（如浏览器已断开），清理实例
                    self._page = None

    @property
    def last_used_time(self):
        return self._last_used_time

    def create_tab(self, url: str = None, no_images: bool = False, no_css: bool = False, proxy: dict = None, proxy_pool_group: str = None, user_agent: str = None):
        """
        线程安全地创建一个新标签页
        
        Args:
            url: 初始 URL
            no_images: 是否禁用图片加载
            no_css: 是否禁用 CSS 加载
            proxy: 手动代理配置
            proxy_pool_group: 代理池分组
            user_agent: User-Agent 字符串
        """
        with self._lock:
            # 如果提供了代理，且当前浏览器已启动，由于 DrissionPage 单例模式限制，
            # 如果当前浏览器代理与请求代理不一致，可能需要重启浏览器。
            # 这里采取简单策略：如果浏览器未启动，或者需要切换代理，则重新初始化。
            
            target_proxy = proxy
            
            # 确保浏览器已初始化
            if not self._page:
                self.get_browser({"proxy": target_proxy, "user_agent": user_agent})
            
            # 更新最后使用时间，防止被空闲检查关闭
            self._last_used_time = time.time()
            
            # 创建新标签页
            tab = self._page.new_tab(url)

            # 设置该标签页的 User-Agent (DrissionPage 支持为单个标签页设置 UA)
            if user_agent:
                try:
                    tab.set.user_agent(user_agent)
                    logger.info(f"Set custom User-Agent for tab: {user_agent}")
                except Exception as e:
                    logger.warning(f"Failed to set custom User-Agent for tab: {e}")
            
            # 动态设置资源拦截
            if no_images:
                # 禁用图片加载
                try:
                    # 优先检测原生 API
                    if hasattr(tab.set, 'img_mode'):
                        tab.set.img_mode(False)
                    elif hasattr(tab.set, 'images'):
                        tab.set.images(False)
                    elif hasattr(tab, 'set_img_mode'):
                        tab.set_img_mode(False)
                    else:
                        # CDP 兜底拦截
                        tab.run_cdp('Network.enable')
                        tab.run_cdp('Network.setBlockedURLs', urls=['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.svg'])
                except Exception as e:
                    logger.warning(f"Failed to set no_images for tab: {e}")
            
            if no_css:
                # 禁用 CSS 加载
                try:
                    # 使用 CDP 网络拦截功能
                    tab.run_cdp('Network.enable')
                    # 也可以尝试直接设置加载策略（如果版本支持）
                    # 这里通过拦截器方式实现更可靠的 CSS 拦截
                    tab.run_cdp('Network.setBlockedURLs', urls=['*.css*', '*stylesheet*'])
                except Exception as e:
                    logger.warning(f"Failed to disable CSS for tab: {e}")
                
            return tab

drission_manager = DrissionManager()
