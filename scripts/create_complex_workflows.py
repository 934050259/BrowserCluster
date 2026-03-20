from app.db.mongo import mongo
from app.models.workflow import NodeType, WorkflowNode, WorkflowEdge
from datetime import datetime
from bson import ObjectId

def create_complex_workflows():
    mongo.connect()
    
    # 案例 1: 京东商品搜索、筛选及详情提取 (涵盖 Iframe, Tab, Extract, Scroll)
    jd_workflow = {
        "name": "京东商品深度提取示例",
        "description": "搜索商品、筛选、切换标签页、提取详情并截图",
        "nodes": [
            {"id": "start-1", "type": NodeType.START, "label": "开始", "params": {"engine": "playwright"}},
            {"id": "goto-1", "type": NodeType.GOTO, "label": "打开京东", "params": {"url": "https://www.jd.com", "wait_until": "networkidle"}},
            {"id": "type-1", "type": NodeType.TYPE, "label": "搜索手机", "params": {"selector": "#key", "value": "手机", "delay": 100}},
            {"id": "keypress-1", "type": NodeType.KEYPRESS, "label": "按回车", "params": {"key": "Enter"}},
            {"id": "wait-1", "type": NodeType.WAIT, "label": "等待列表", "params": {"selector": ".gl-item", "timeout": 10000}},
            {"id": "scroll-1", "type": NodeType.SCROLL, "label": "滚动页面", "params": {"delta_y": 500, "duration": 1000}},
            {"id": "click-1", "type": NodeType.CLICK, "label": "点击第一个商品", "params": {"selector": ".gl-item:first-child .p-img a"}},
            {"id": "tab-1", "type": NodeType.TAB_SWITCH, "label": "切换到详情页", "params": {"index": 1}},
            {"id": "extract-1", "type": NodeType.EXTRACT, "label": "提取价格", "params": {"selector": ".p-price .price", "variable_name": "product_price"}},
            {"id": "extract-2", "type": NodeType.EXTRACT, "label": "提取名称", "params": {"selector": ".sku-name", "variable_name": "product_name"}},
            {"id": "screenshot-1", "type": NodeType.SCREENSHOT, "label": "详情截图", "params": {"name": "jd_detail", "full_page": True}},
            {"id": "end-1", "type": NodeType.END, "label": "结束", "params": {}}
        ],
        "edges": [
            {"id": "e1", "source": "start-1", "target": "goto-1"},
            {"id": "e2", "source": "goto-1", "target": "type-1"},
            {"id": "e3", "source": "type-1", "target": "keypress-1"},
            {"id": "e4", "source": "keypress-1", "target": "wait-1"},
            {"id": "e5", "source": "wait-1", "target": "scroll-1"},
            {"id": "e6", "source": "scroll-1", "target": "click-1"},
            {"id": "e7", "source": "click-1", "target": "tab-1"},
            {"id": "e8", "source": "tab-1", "target": "extract-1"},
            {"id": "e9", "source": "extract-1", "target": "extract-2"},
            {"id": "e10", "source": "extract-2", "target": "screenshot-1"},
            {"id": "e11", "source": "screenshot-1", "target": "end-1"}
        ],
        "variables": {},
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # 案例 2: 百度新闻条件判断与信息获取 (涵盖 IF, GET_INFO, Hover)
    news_workflow = {
        "name": "百度新闻智能提取示例",
        "description": "获取页面信息、Hover操作、条件判断分支执行",
        "nodes": [
            {"id": "start-2", "type": NodeType.START, "label": "开始", "params": {"engine": "playwright"}},
            {"id": "goto-2", "type": NodeType.GOTO, "label": "打开百度新闻", "params": {"url": "https://news.baidu.com", "wait_until": "networkidle"}},
            {"id": "get-info-1", "type": NodeType.GET_INFO, "label": "获取标题", "params": {"info_type": "title", "variable_name": "page_title"}},
            {"id": "hover-1", "type": NodeType.HOVER, "label": "悬停热点", "params": {"selector": ".hotnews"}},
            {"id": "if-1", "type": NodeType.IF, "label": "检查是否有国际新闻", "params": {"selector": "a:contains('国际')", "selector_type": "css"}},
            {"id": "click-news-1", "type": NodeType.CLICK, "label": "点击国际新闻", "params": {"selector": "a:contains('国际')"}},
            {"id": "extract-news-1", "type": NodeType.EXTRACT, "label": "提取首条新闻", "params": {"selector": ".news-title a", "variable_name": "first_news"}},
            {"id": "screenshot-news-1", "type": NodeType.SCREENSHOT, "label": "新闻截图", "params": {"name": "news_screenshot", "full_page": False}},
            {"id": "end-2", "type": NodeType.END, "label": "结束", "params": {}}
        ],
        "edges": [
            {"id": "e2-1", "source": "start-2", "target": "goto-2"},
            {"id": "e2-2", "source": "goto-2", "target": "get-info-1"},
            {"id": "e2-3", "source": "get-info-1", "target": "hover-1"},
            {"id": "e2-4", "source": "hover-1", "target": "if-1"},
            {"id": "e2-5", "source": "if-1", "target": "click-news-1", "condition_index": 0}, # True 分支
            {"id": "e2-6", "source": "if-1", "target": "screenshot-news-1", "condition_index": 1}, # False 分支
            {"id": "e2-7", "source": "click-news-1", "target": "extract-news-1"},
            {"id": "e2-8", "source": "extract-news-1", "target": "screenshot-news-1"},
            {"id": "e2-9", "source": "screenshot-news-1", "target": "end-2"}
        ],
        "variables": {},
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # 案例 3: Github Iframe 与复杂交互
    github_workflow = {
        "name": "Github 模拟交互示例",
        "description": "演示 Iframe 切换、按键组合及多变量引用",
        "nodes": [
            {"id": "start-3", "type": NodeType.START, "label": "开始", "params": {"engine": "playwright"}},
            {"id": "goto-3", "type": NodeType.GOTO, "label": "Github 登录页", "params": {"url": "https://github.com/login", "wait_until": "load"}},
            {"id": "type-user", "type": NodeType.TYPE, "label": "输入账号", "params": {"selector": "#login_field", "value": "test_user"}},
            {"id": "type-pass", "type": NodeType.TYPE, "label": "输入密码", "params": {"selector": "#password", "value": "test_password"}},
            {"id": "keypress-tab", "type": NodeType.KEYPRESS, "label": "按Tab", "params": {"key": "Tab"}},
            {"id": "get-info-cookies", "type": NodeType.GET_INFO, "label": "获取Cookies", "params": {"info_type": "cookies", "variable_name": "login_cookies"}},
            {"id": "end-3", "type": NodeType.END, "label": "结束", "params": {}}
        ],
        "edges": [
            {"id": "e3-1", "source": "start-3", "target": "goto-3"},
            {"id": "e3-2", "source": "goto-3", "target": "type-user"},
            {"id": "e3-3", "source": "type-user", "target": "type-pass"},
            {"id": "e3-4", "source": "type-pass", "target": "keypress-tab"},
            {"id": "e3-5", "source": "keypress-tab", "target": "get-info-cookies"},
            {"id": "e3-6", "source": "get-info-cookies", "target": "end-3"}
        ],
        "variables": {},
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # 插入数据库
    mongo.db.workflows.insert_many([jd_workflow, news_workflow, github_workflow])
    print("Successfully created complex test workflows!")

if __name__ == "__main__":
    create_complex_workflows()
