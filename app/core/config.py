"""
应用配置管理模块

使用 pydantic_settings 从环境变量或 .env 文件加载配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""

    # FastAPI 配置
    app_name: str = Field(default="BrowserCluster", description="应用名称，用于标识系统")
    app_version: str = Field(default="1.0.0", description="系统当前版本号")
    debug: bool = Field(default=True, description="调试模式开关，开启后会输出详细日志")
    host: str = Field(default="0.0.0.0", description="服务监听的主机地址")
    port: int = Field(default=8000, description="服务监听的端口号")

    # MongoDB 配置
    mongo_uri: str = Field(default="mongodb://localhost:27017/", description="MongoDB 连接地址")
    mongo_db: str = Field(default="browser_cluster", description="MongoDB 数据库名称")

    # Redis 配置
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis 连接 URL，用于任务队列和代理池等")
    redis_cache_url: str = Field(default="redis://localhost:6379/1", description="Redis 缓存连接 URL，用于存储抓取结果缓存")

    # RabbitMQ 配置
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", description="RabbitMQ 消息队列连接 URL")
    rabbitmq_queue: str = Field(default="scrape_tasks", description="RabbitMQ 默认任务队列名称")
    rabbitmq_exchange: str = Field(default="browser_cluster", description="RabbitMQ 交换机名称")

    # 浏览器配置
    browser_type: str = Field(default="chromium", description="默认浏览器类型 (chromium, firefox, webkit)")
    browser_engine: str = Field(default="playwright", description="浏览器驱动引擎 (playwright, drissionpage)")
    headless: bool = Field(default=True, description="是否以无头模式运行浏览器")
    block_images: bool = Field(default=False, description="是否拦截图片加载")
    block_media: bool = Field(default=False, description="是否拦截媒体资源加载 (视频/音频)")
    default_timeout: int = Field(default=30000, description="默认任务超时时间 (毫秒)")
    default_wait_for: str = Field(default="networkidle", description="默认页面等待策略 (networkidle, load, domcontentloaded)")
    default_viewport_width: int = Field(default=1920, description="默认浏览器视口宽度")
    default_viewport_height: int = Field(default=1080, description="默认浏览器视口高度")
    user_agent: str = Field(default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", description="默认浏览器 User-Agent")
    browser_idle_timeout: int = Field(default=1800, description="浏览器实例空闲超时时间 (秒)")
    stealth_mode: bool = Field(default=True, description="是否默认开启反爬虫隐身模式")

    # Worker 配置
    worker_concurrency: int = Field(default=3, description="单个 Worker 节点的并发任务数")
    retry_enabled: bool = Field(default=True, description="是否启用任务失败自动重试")
    max_retries: int = Field(default=3, description="任务失败最大重试次数")
    retry_delay: int = Field(default=5, description="任务重试延迟时间 (秒)")

    # 缓存配置
    cache_enabled: bool = Field(default=True, description="是否全局启用结果缓存")
    default_cache_ttl: int = Field(default=3600, description="默认缓存过期时间 (秒)")

    # 节点配置
    node_id: str = Field(default="node-1", description="当前工作节点的唯一标识符")
    node_type: str = Field(default="worker", description="当前节点类型 (master/worker)")
    heartbeat_interval: int = Field(default=30, description="节点心跳上报间隔 (秒)")
    max_node_auto_retries: int = Field(default=5, description="节点异常自动重启最大尝试次数")

    # 大模型解析配置
    llm_api_base: str = Field(default="https://api.openai.com/v1", description="大语言模型 API 基础地址")
    llm_api_key: str = Field(default="", description="大语言模型 API 密钥")
    llm_model: str = Field(default="gpt-3.5-turbo", description="大语言模型模型名称")

    # OSS 存储配置
    oss_enabled: bool = Field(default=False, description="是否启用 OSS 存储，开启后 HTML 和截图将上传至阿里云 OSS")
    oss_endpoint: str = Field(default="oss-cn-hangzhou.aliyuncs.com", description="OSS 访问域名")
    oss_access_key_id: str = Field(default="", description="OSS AccessKey ID")
    oss_access_key_secret: str = Field(default="", description="OSS AccessKey Secret")
    oss_bucket_name: str = Field(default="", description="OSS Bucket 名称")
    oss_bucket_domain: str = Field(default="", description="OSS 自定义域名或默认域名 (用于生成访问 URL)")

    # 代理池配置
    proxy_enable_check: bool = Field(default=True, description="是否启用代理可用性自动检测")
    proxy_redis_db: int = Field(default=6, description="代理池使用的 Redis 数据库索引")
    proxy_redis_key_prefix: str = Field(default="proxy_pool", description="代理池 Redis Key 前缀")
    proxy_check_url: str = Field(default="https://myip.ipip.net/", description="代理检测时使用的目标 URL")
    proxy_check_interval: int = Field(default=300, description="代理检测周期 (秒)")
    proxy_check_timeout: float = Field(default=10.0, description="单个代理检测超时时间 (秒)")
    proxy_fail_threshold: int = Field(default=3, description="代理连续失效多少次后标记为不可用")

    # 日志配置
    log_level: str = Field(default="INFO", description="系统日志打印级别 (DEBUG, INFO, WARNING, ERROR)")
    log_file: str = Field(default="logs/app.log", description="系统日志文件保存路径")

    # 安全配置
    secret_key: str = Field(default="your-secret-key-here", description="系统安全密钥，用于 Token 签名等")
    algorithm: str = Field(default="HS256", description="Token 签名加密算法")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, description="Token 有效期时长 (分钟)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    def load_from_db(self):
        """从 SQLite 数据库加载动态配置"""
        try:
            from app.db.sqlite import sqlite_db
            db_configs = {c['key']: c['value'] for c in sqlite_db.get_all_configs()}
            
            # 创建一个临时实例以获取基准值（代码默认值 + .env 环境变量）
            # 这确保了如果某个配置从数据库删除，它能恢复到基准值
            # 使用 type(self)() 创建新实例，避免直接引用 Settings 类名（虽然在这里没区别）
            base_settings = self.__class__()
            
            updated_count = 0
            reset_count = 0
            # 遍历所有定义的字段
            for key in self.model_fields.keys():
                # 如果数据库中有该配置，使用数据库的值覆盖
                if key in db_configs:
                    value = db_configs[key]
                    # 获取基准值的类型用于转换
                    base_value = getattr(base_settings, key)
                    target_type = type(base_value)
                    
                    try:
                        # 类型转换
                        if target_type == bool:
                            if isinstance(value, bool):
                                new_value = value
                            else:
                                new_value = str(value).lower() in ('true', '1', 'yes', 'on')
                        elif target_type == int:
                            new_value = int(value)
                        elif target_type == float:
                            new_value = float(value)
                        else:
                            new_value = str(value)
                            
                        setattr(self, key, new_value)
                        updated_count += 1
                    except (ValueError, TypeError):
                        # 如果转换失败，保持基准值
                        setattr(self, key, base_value)
                        continue
                else:
                    # 如果数据库中没有该配置，还原为基准值
                    # 这解决了删除数据库项后内存中仍保留旧值的问题
                    base_value = getattr(base_settings, key)
                    if getattr(self, key) != base_value:
                        setattr(self, key, base_value)
                        reset_count += 1
            
            if updated_count > 0 or reset_count > 0:
                print(f"Configuration sync complete: {updated_count} updated from DB, {reset_count} reset to defaults")
                    
        except Exception as e:
            print(f"Error loading configs from DB: {e}")


# 全局配置实例
settings = Settings()