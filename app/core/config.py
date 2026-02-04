"""
应用配置管理模块

使用 pydantic_settings 从环境变量或 .env 文件加载配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # FastAPI 配置
    app_name: str = "BrowserCluster"  # 应用名称
    app_version: str = "1.0.0"  # 应用版本
    debug: bool = True  # 调试模式
    host: str = "0.0.0.0"  # 监听地址
    port: int = 8000  # 监听端口

    # MongoDB 配置
    mongo_uri: str = "mongodb://localhost:27017/"  # MongoDB 连接地址
    mongo_db: str = "browser_cluster"  # 数据库名称

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"  # Redis 队列连接地址
    redis_cache_url: str = "redis://localhost:6379/1"  # Redis 缓存连接地址

    # RabbitMQ 配置
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"  # RabbitMQ 连接地址
    rabbitmq_queue: str = "scrape_tasks"  # 任务队列名称
    rabbitmq_exchange: str = "browser_cluster"  # 交换机名称

    # Playwright 配置
    browser_type: str = "chromium"  # 浏览器类型
    headless: bool = True  # 是否无头模式
    block_images: bool = False  # 是否拦截图片
    block_media: bool = False  # 是否拦截媒体资源
    default_timeout: int = 30000  # 默认超时时间（毫秒）
    default_wait_for: str = "networkidle"  # 默认等待策略
    default_viewport_width: int = 1920  # 默认视口宽度
    default_viewport_height: int = 1080  # 默认视口高度
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"  # 默认 User-Agent
    browser_idle_timeout: int = 300  # 浏览器空闲超时时间（秒），默认5分钟
    stealth_mode: bool = True  # 默认隐蔽模式

    # Worker 配置
    worker_concurrency: int = 3  # Worker 并发数
    max_retries: int = 3  # 最大重试次数
    retry_delay: int = 5  # 重试延迟（秒）

    # 缓存配置
    cache_enabled: bool = True  # 是否启用缓存
    default_cache_ttl: int = 3600  # 默认缓存过期时间（秒）

    # 节点配置
    node_id: str = "node-1"  # 节点 ID
    node_type: str = "worker"  # 节点类型
    heartbeat_interval: int = 30  # 心跳间隔（秒）
    max_node_auto_retries: int = 5  # 节点自动重启最大重试次数

    # 大模型解析配置
    llm_api_base: str = "https://api.openai.com/v1"  # LLM API 基础地址
    llm_api_key: str = ""  # LLM API 密钥
    llm_model: str = "gpt-3.5-turbo"  # LLM 模型名称

    # 日志配置
    log_level: str = "INFO"  # 日志级别
    log_file: str = "logs/app.log"  # 日志文件路径

    # 安全配置
    secret_key: str = "your-secret-key-here"  # 应该在 .env 中设置
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7天

    class Config:
        """Pydantic 配置类"""
        env_file = ".env"  # 环境变量文件

    def load_from_db(self):
        """从 SQLite 数据库加载动态配置"""
        try:
            from app.db.sqlite import sqlite_db
            configs = sqlite_db.get_all_configs()
            
            updated_count = 0
            for config in configs:
                key = config['key']
                value = config['value']
                
                # 仅更新已存在的配置项
                if hasattr(self, key):
                    # 获取当前值的类型
                    current_value = getattr(self, key)
                    target_type = type(current_value)
                    
                    try:
                        # 类型转换
                        if target_type == bool:
                            # 处理布尔值
                            if str(value).lower() in ('true', '1', 'yes', 'on'):
                                new_value = True
                            else:
                                new_value = False
                        elif target_type == int:
                            new_value = int(value)
                        elif target_type == float:
                            new_value = float(value)
                        else:
                            new_value = str(value)
                            
                        setattr(self, key, new_value)
                        updated_count += 1
                    except ValueError:
                        print(f"Warning: Failed to convert config '{key}' value '{value}' to {target_type}")
                        continue
                        
            if updated_count > 0:
                print(f"Loaded {updated_count} configurations from SQLite database")
                
        except Exception as e:
            print(f"Error loading configs from DB: {e}")


# 全局配置实例
settings = Settings()