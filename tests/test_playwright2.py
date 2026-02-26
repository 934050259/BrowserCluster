from playwright.sync_api import sync_playwright
import time
import random


def check_detection(page):
    """检查是否被检测为机器人"""
    detection_indicators = page.evaluate("""
        () => {
            const indicators = {};
            
            // 检查 navigator.webdriver
            indicators.webdriver = navigator.webdriver === true;
            
            // 检查 chrome 属性
            indicators.hasChrome = typeof window.chrome !== 'undefined';
            indicators.chromeRuntime = window.chrome && window.chrome.runtime;
            
            // 检查插件数量
            indicators.pluginsLength = navigator.plugins.length;
            
            // 检查 languages
            indicators.languages = navigator.languages;
            
            // 检查 permissions
            indicators.permissions = navigator.permissions;
            
            return indicators;
        }
    """)
    
    print("检测指标:", detection_indicators)
    
    if detection_indicators.get('webdriver'):
        print("⚠️ 被检测到自动化！")
        return True
    return False


with sync_playwright() as p:
    # 1. 使用无头模式或添加参数
    browser = p.chromium.launch(
        executable_path=r'C:\Users\Administrator\AppData\Local\Chromium\Application\chrome.exe' ,
        
        headless=False,  # 使用有头模式
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-back-forward-cache',
            '--disable-component-update',
            '--disable-domain-reliability',
            '--disable-client-side-phishing-detection',
            '--disable-sync',
            '--metrics-recording-only',
            '--disable-default-apps',
            '--mute-audio',
            '--no-default-browser-check',
            '--no-first-run',
            '--use-fake-device-for-media-stream',
            '--use-fake-ui-for-media-stream',
            '--autoplay-policy=no-user-gesture-required',
        ]
    )
    
    # 2. 创建上下文时添加额外参数
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        permissions=['geolocation'],
        # 设置更真实的设备信息
        device_scale_factor=1,
        has_touch=False,
        is_mobile=False,
        java_script_enabled=True,
    )
    
    # 3. 注入 JavaScript 移除自动化特征
    context.add_init_script("""
        // 移除 webdriver 属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // 修改 languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        
        // 修改 plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // 覆盖 chrome 属性
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // 隐藏 permissions 中的 automation
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // 修改 navigator 属性
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
        
        // 添加一些真实浏览器才会有的属性
        Object.defineProperty(document, 'hidden', {
            get: () => false
        });
        
        Object.defineProperty(document, 'visibilityState', {
            get: () => 'visible'
        });
    """)
    
    page = context.new_page()

    check_detection(page)

    # 4. 访问页面
    page.goto('https://www.bayut.com/for-sale/off-plan/property/uae/', wait_until='networkidle')
    
    # 5. 随机化鼠标移动
    # simulate_human_mouse_movement(page)
    
    # 6. 模拟人类输入
    # if page.is_visible('input'):
        # simulate_human_typing(page, 'input', '搜索内容')
    
    # 保持页面打开
    time.sleep(10)
    
    page.click("aaaa")
    browser.close()

def simulate_human_mouse_movement(page):
    """模拟人类鼠标移动"""
    # 移动到随机位置
    page.mouse.move(
        random.randint(100, 500),
        random.randint(100, 500)
    )
    
    # 随机移动鼠标
    for _ in range(random.randint(3, 7)):
        page.mouse.move(
            random.randint(0, 1000),
            random.randint(0, 800),
            steps=random.randint(20, 50)  # 步骤越多越像真人
        )
        time.sleep(random.uniform(0.1, 0.3))

def simulate_human_typing(page, selector, text):
    """模拟人类打字"""
    page.click(selector)
    time.sleep(random.uniform(0.5, 1.5))
    
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.2))  # 随机延迟
        
    # 偶尔删除重输
    if random.random() < 0.3:
        for _ in range(random.randint(1, 3)):
            page.keyboard.press('Backspace')
            time.sleep(random.uniform(0.1, 0.3))
        page.keyboard.type(text[-random.randint(1, 3):])