"""
日志管理模块

配置全局日志格式、处理器（控制台和文件）以及级别
"""
import os
import logging
import threading
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# 用于存储每个线程的节点 ID
thread_local = threading.local()

class NodeFilter(logging.Filter):
    """
    根据线程局部的 node_id 过滤日志
    """
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    def filter(self, record):
        # 如果线程局部存储中有 node_id 且匹配，则通过
        current_node_id = getattr(thread_local, "node_id", None)
        return current_node_id == self.node_id

def setup_logging():
    """
    初始化全局日志配置
    """
    # 确保日志目录存在
    log_file = settings.log_file
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # 防止重复添加处理器
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 主应用文件处理器（支持自动轮转）
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        # 主日志文件记录所有非节点特定的日志，或者记录所有日志？
        # 通常主日志记录所有日志比较好，节点日志只记录该节点的日志。
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to set up file logging: {e}")

    # 设置第三方库的日志级别，避免干扰
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    return root_logger

def setup_node_logger(node_id: str):
    """
    为特定节点设置日志处理器
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"node-{node_id}.log")
    
    # 设置线程局部的 node_id
    thread_local.node_id = node_id
    
    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 检查是否已经存在该节点的处理器（防止重复添加）
    handler_name = f"node_handler_{node_id}"
    for h in root_logger.handlers:
        if h.get_name() == handler_name:
            return
            
    # 创建文件处理器
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 节点日志 5MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.set_name(handler_name)
        
        # 添加过滤器，只记录当前线程（即该节点）产生的日志
        node_filter = NodeFilter(node_id)
        file_handler.addFilter(node_filter)
        
        root_logger.addHandler(file_handler)
        logging.info(f"Initialized specific logger for node: {node_id}")
    except Exception as e:
        logging.error(f"Failed to set up specific logger for node {node_id}: {e}")
