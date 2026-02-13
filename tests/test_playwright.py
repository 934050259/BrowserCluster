import re

import asyncio
import logging
import sys
import threading
import time
from typing import Optional
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    # 启动浏览器参数
    launch_args = []
    launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ])
    
    browser = playwright.chromium.launch(
        executable_path=r'C:\Users\Administrator\AppData\Local\Chromium\Application\chrome.exe' ,
        headless=False,
        args=launch_args
    )

    page = browser.new_page()
    page.goto('https://www.bayut.com/for-sale/off-plan/property/uae/')
    print(page.title())
    
    page.click("aaa")
    browser.close()