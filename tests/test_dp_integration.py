import sys
import os
import time
import base64

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.drission_browser import DrissionManager
from app.core.config import settings

def test_cloudflare_bypass():
    """测试 DrissionPage 绕过 Cloudflare 5秒盾"""
    # 目标网站 (已知有 Cloudflare 保护)
    # test_url = "https://cn.airbusan.com/content/common/customercenter/noticeList"
    # test_url = "https://toppsta.com/books/series/29278/national-geographic-kids-readers-level-1"
    test_url = "https://www.mediamarkt.de/de/product/_ecg-nm-2255-milk-frother-black-90790545.html"
    print(f"[*] 正在启动测试，目标地址: {test_url}")
    
    # 初始化管理器
    manager = DrissionManager()
    
    # 获取浏览器单例
    params = {
        "headless": False,  # 测试时建议开启有头模式观察
        "timeout": 30000
    }
    
    try:
        print("[*] 正在启动/获取浏览器实例...")
        browser = manager.get_browser(params)
        
        print("[*] 创建新标签页...")
        tab = browser.new_tab()
        
        print(f"[*] 正在访问页面 (设置 30s 超时)...")
        tab.get(test_url, timeout=30)
        
        # 处理 Cloudflare 挑战逻辑 (参考 scraper.py 实现)
        print("[*] 正在等待 Cloudflare 挑战通过 (最长等待 60s)...")
        wait_start = time.time()
        max_wait = 60
        
        while time.time() - wait_start < max_wait:
            html_lower = tab.html.lower()
            title = tab.title
            
            # 判断是否通过挑战
            if "checking your browser" not in html_lower and \
               "just a moment" not in html_lower and \
               "请稍候" not in title and \
               "验证您是否是真人" not in title:
                print("[+] Cloudflare 挑战似乎已绕过!")
                break

            try:
                # 尝试点击 Cloudflare 的典型中心区域
                tab.ele(".ctp-button").click()
                print("[*] 尝试点击验证按钮...")
            except:
                pass
            
            # 尝试查找并点击潜在的验证按钮 (iframe 外部或简单的 div 按钮)
            try:
                # 尝试点击 Cloudflare 的典型中心区域
                tab.ele("x://div[@class='main-content']/div[1]", timeout=5).click.at(30, 30)
                tab.ele("x://div[@class='main-content']/div[1]", timeout=5).click.at(40, 40)
                print("[*] 尝试点击验证区域...")
            except:
                pass

            #尝试查找并点击潜在的验证按钮 (iframe 外部或简单的 div 按钮)
            try:
                # 尝试点击 Cloudflare 的典型中心区域
                tab.ele("x://div[@style='display: grid;']", timeout=5).click.at(30, 30)
                tab.ele("x://div[@style='display: grid;']", timeout=5).click.at(40, 40)
                print("[*] 尝试点击验证区域...")
            except:
                pass
                
            # 检查是否有 iframe (针对 Turnstile)
            try:
                iframes = tab.eles('tag:iframe')
                for iframe in iframes:
                    src = iframe.attr('src') or ''
                    if 'cloudflare' in src or 'turnstile' in src:
                        print(f"[*] 发现验证 iframe: {src}")
                        # 这里可以进一步实现 iframe 内部点击逻辑
                        # 暂时依赖 DrissionPage 的自动抗检测能力
            except:
                pass

            print(f"[*] 还在等待中... (当前标题: {title})")
            time.sleep(3)
        else:
            print("[-] 等待超时，可能未能绕过 5s 盾。")
            
        # 验证结果
        print("-" * 50)
        print(f"最终标题: {tab.title}")
        print(f"当前 URL: {tab.url}")
        
        if "Gold Rate" in tab.title:
            print("[SUCCESS] 成功进入目标网站!")
        else:
            print("[FAILED] 未能识别到目标网站特征。")
            
        # 截图保存 (可选)
        screenshot_path = "cf_bypass_result.png"
        tab.get_screenshot(path=screenshot_path, full_page=True)
        print(f"[*] 结果截图已保存至: {screenshot_path}")
        
        # 获取 Cookie
        cookies = tab.cookies()
        print(f"[*] 获取到 Cookie 数量: {len(cookies)}")
        
    except Exception as e:
        print(f"[!] 测试过程中出现错误: {e}")
    finally:
        # 在测试脚本中，我们可以选择关闭浏览器或保持打开
        # 由于是单例模式，这里不主动关闭，除非需要结束所有测试
        # manager.close_browser()
        print("[*] 测试结束。")

if __name__ == "__main__":
    test_cloudflare_bypass()
