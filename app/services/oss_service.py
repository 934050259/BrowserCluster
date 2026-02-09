"""
OSS 存储服务模块

提供文件上传到阿里云 OSS 的功能
"""
import logging
import oss2
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class OSSService:
    """OSS 存储服务类"""

    def __init__(self):
        self._auth = None
        self._bucket = None
        self._initialized = False
        self._last_config = {}

    def _initialize(self, force: bool = False) -> bool:
        """初始化 OSS 客户端"""
        # 如果没有强制初始化，且全局开关关闭，则不初始化
        if not force and not settings.oss_enabled:
            return False

        # 检查配置是否完整
        current_config = {
            "id": settings.oss_access_key_id,
            "secret": settings.oss_access_key_secret,
            "endpoint": settings.oss_endpoint,
            "bucket": settings.oss_bucket_name
        }

        # 如果已经初始化过，且配置没有变化，直接返回 True
        if self._initialized and self._last_config == current_config:
            return True

        if not all(current_config.values()):
            logger.warning(f"OSS configuration is incomplete: {current_config}")
            return False

        try:
            self._auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
            self._bucket = oss2.Bucket(self._auth, settings.oss_endpoint, settings.oss_bucket_name)
            self._initialized = True
            self._last_config = current_config
            logger.info("OSS client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OSS client: {e}")
            self._initialized = False
            return False

    def upload_content(self, content: str, filename: str, content_type: str = "text/html", force: bool = False) -> Optional[str]:
        """
        上传内容到 OSS

        Args:
            content: 内容字符串 (HTML 或 Base64)
            filename: 文件名
            content_type: 内容类型
            force: 是否忽略 settings.oss_enabled 开关强制上传

        Returns:
            Optional[str]: 上传后的访问 URL，如果失败则返回 None
        """
        if not self._initialize(force):
            return None

        try:
            # 如果是 base64 截图，需要先解码
            if content_type.startswith("image/"):
                import base64
                if "," in content:
                    content = content.split(",")[1]
                data = base64.b64decode(content)
            else:
                data = content.encode('utf-8')

            # 上传到 OSS
            result = self._bucket.put_object(filename, data, headers={"Content-Type": content_type})
            
            if result.status == 200:
                # 生成访问 URL
                domain = settings.oss_bucket_domain or f"{settings.oss_bucket_name}.{settings.oss_endpoint}"
                if not domain.startswith("http"):
                    domain = f"https://{domain}"
                
                url = f"{domain}/{filename}"
                logger.info(f"Successfully uploaded {filename} to OSS: {url}")
                return url
            else:
                logger.error(f"Failed to upload {filename} to OSS, status: {result.status}")
                return None
        except Exception as e:
            logger.error(f"Error uploading {filename} to OSS: {e}")
            return None

    def upload_task_assets(self, task_id: str, html: Optional[str], screenshot: Optional[str], force: bool = False, custom_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        上传任务的 HTML 和截图到 OSS

        Args:
            task_id: 任务 ID
            html: HTML 内容
            screenshot: 截图 Base64
            force: 是否强制上传
            custom_path: 自定义存储路径 (例如: mydata/2024/)

        Returns:
            Tuple[Optional[str], Optional[str]]: (html_url, screenshot_url)
        """
        html_url = None
        screenshot_url = None

        # 确定基础路径
        base_path = f"tasks/{task_id}"
        if custom_path:
            # 确保自定义路径以 / 结尾
            custom_path = custom_path if custom_path.endswith('/') else f"{custom_path}/"
            base_path = f"{custom_path}{task_id}"

        if html:
            html_filename = f"{base_path}/index.html"
            html_url = self.upload_content(html, html_filename, "text/html", force=force)

        if screenshot:
            screenshot_filename = f"{base_path}/screenshot.png"
            screenshot_url = self.upload_content(screenshot, screenshot_filename, "image/png", force=force)

        return html_url, screenshot_url

    def get_content(self, filename_or_url: str) -> Optional[bytes]:
        """
        通过 OSS SDK 获取文件内容 (支持私有 Bucket)

        Args:
            filename_or_url: 文件名或完整的 OSS URL

        Returns:
            Optional[bytes]: 文件二进制内容，失败返回 None
        """
        if not self._initialize(force=True):
            return None

        try:
            # 如果传入的是 URL，提取出 filename
            filename = filename_or_url
            if filename.startswith("http"):
                # 假设 URL 格式为 https://bucket.endpoint/path/to/file
                from urllib.parse import urlparse
                parsed_url = urlparse(filename_or_url)
                # 路径部分，去掉开头的 /
                filename = parsed_url.path.lstrip('/')
            
            logger.info(f"Fetching content from OSS: {filename}")
            result = self._bucket.get_object(filename)
            return result.read()
        except Exception as e:
            logger.error(f"Error fetching {filename_or_url} from OSS: {e}")
            return None

# 全局 OSS 服务实例
oss_service = OSSService()
