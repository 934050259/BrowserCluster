#!/usr/bin/env python3
"""
Worker 启动脚本

启动 Worker 进程，开始消费和处理任务
"""
import os
import sys
import asyncio

# Windows 平台下，Playwright 需要使用 ProactorEventLoopPolicy 才能正常启动子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.worker import start_worker
from app.core.logger import setup_logging

if __name__ == "__main__":
    # 初始化日志
    setup_logging()
    
    # 启动 Worker
    asyncio.run(start_worker())
