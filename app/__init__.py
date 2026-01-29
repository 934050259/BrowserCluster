import asyncio
import sys

# Windows 平台下，Playwright 需要使用 ProactorEventLoopPolicy 才能正常启动子进程
# 必须在任何事件循环创建之前设置
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
