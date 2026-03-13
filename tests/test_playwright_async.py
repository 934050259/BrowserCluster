#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 最简异步 Demo
功能：启动浏览器，访问页面，截图，关闭
"""

import asyncio
from playwright.async_api import async_playwright


async def simplest_demo():
    """
    最简单的 Playwright 异步示例
    """
    print("🚀 开始最简单的 Playwright Demo")
    
    # 1. 创建 Playwright 实例
    async with async_playwright() as p:
        # 2. 启动浏览器（Chromium）
        browser = await p.chromium.launch(
            headless=False ,  # 显示浏览器窗口
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # 3. 创建页面上下文
        context = await browser.new_context()
        
        # 4. 创建新页面
        page = await context.new_page()
        
        # 5. 导航到页面
        print("🌐 正在访问百度...")
        await page.goto('https://www.bayut.com/for-sale/off-plan/property/uae/')
        
        # 6. 获取页面标题
        title = await page.title()
        print(f"📄 页面标题: {title}")
        
        # 7. 截图
        await page.screenshot(path='baidu_screenshot.png')
        print("📸 截图已保存: baidu_screenshot.png")
        
        # 8. 等待几秒钟查看效果
        print("⏳ 等待 5 秒...")
        await asyncio.sleep(5)
        
        # 9. 关闭浏览器（自动清理资源）
        await browser.close()
    
    print("✅ Demo 完成！")


# 运行异步函数
asyncio.run(simplest_demo())