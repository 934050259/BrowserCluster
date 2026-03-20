from app.db.mongo import mongo
from app.models.workflow import NodeType
from datetime import datetime
import json

def create_ultimate_workflows():
    mongo.connect()
    
    # 案例 4: 菜鸟教程 综合测试 (无验证码)
    # 涵盖: Start, Goto, Wait, Hover, Type, Keypress, Click, Tab_Switch, Scroll, Extract, Get_Info, Screenshot, End
    runoob_workflow = {
        "name": "菜鸟教程全功能演示 (无验证码)",
        "description": "搜索教程 -> 切新标签页 -> 滚动获取 -> 提取代码 -> 截图验证",
        "nodes": [
            # 1. 基础启动与配置
            {"id": "n1", "type": NodeType.START, "label": "开始", "params": {
                "engine": "playwright",
                "headers": json.dumps({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            }, "position": {"x": 100, "y": 50}},
            
            # 2. 访问首页
            {"id": "n2", "type": NodeType.GOTO, "label": "打开菜鸟教程", "params": {"url": "https://www.runoob.com/", "wait_until": "domcontentloaded", "timeout": 30000}, "position": {"x": 100, "y": 150}},
            
            # 3. 基础获取
            {"id": "n3", "type": NodeType.GET_INFO, "label": "获取页面标题", "params": {"info_type": "title", "variable_name": "home_title"}, "position": {"x": 100, "y": 250}},
            
            # 4. 表单与按键 (菜鸟搜索框)
            {"id": "n4", "type": NodeType.TYPE, "label": "输入搜索词", "params": {"selector": "#s", "value": "Python 列表", "delay": 50, "selector_type": "css"}, "position": {"x": 100, "y": 350}},
            {"id": "n5", "type": NodeType.KEYPRESS, "label": "按回车搜索", "params": {"key": "Enter", "delay": 200}, "position": {"x": 100, "y": 450}},
            
            # 5. 等待与点击 (菜鸟搜索结果会新开标签页)
            {"id": "n6", "type": NodeType.WAIT, "label": "等待新标签", "params": {"timeout": 3000}, "position": {"x": 100, "y": 550}},
            {"id": "n7", "type": NodeType.TAB_SWITCH, "label": "切换到搜索结果页", "params": {"index": 1}, "position": {"x": 100, "y": 650}},
            
            # 6. 等待结果并点击第一条
            {"id": "n8", "type": NodeType.WAIT, "label": "等待结果列表", "params": {"selector": ".search-result", "selector_type": "css", "timeout": 10000}, "position": {"x": 350, "y": 150}},
            {"id": "n9", "type": NodeType.CLICK, "label": "点击第一条结果", "params": {"selector": ".search-result .search-item:first-child a", "selector_type": "css", "timeout": 5000}, "position": {"x": 350, "y": 250}},
            
            # 7. 切换到具体的教程页面 (第三个标签)
            {"id": "n10", "type": NodeType.WAIT, "label": "等待教程标签", "params": {"timeout": 3000}, "position": {"x": 350, "y": 350}},
            {"id": "n11", "type": NodeType.TAB_SWITCH, "label": "切换到教程页", "params": {"index": 2}, "position": {"x": 350, "y": 450}},
            
            # 8. 滚动与悬停提取
            {"id": "n12", "type": NodeType.SCROLL, "label": "向下滚动", "params": {"delta_y": 500, "duration": 1000}, "position": {"x": 350, "y": 550}},
            {"id": "n13", "type": NodeType.EXTRACT, "label": "提取大标题", "params": {"selector": "h1", "variable_name": "tutorial_title", "selector_type": "css"}, "position": {"x": 350, "y": 650}},
            {"id": "n14", "type": NodeType.EXTRACT, "label": "提取第一段代码", "params": {"selector": ".hl-main", "variable_name": "first_code_snippet", "selector_type": "css"}, "position": {"x": 600, "y": 150}},
            
            # 9. IF 条件测试
            {"id": "n15", "type": NodeType.IF, "label": "是否存在运行实例?", "params": {"selector": ".tryitbtn", "selector_type": "css"}, "position": {"x": 600, "y": 250}},
            {"id": "n16", "type": NodeType.GET_INFO, "label": "记录有运行功能", "params": {"info_type": "url", "variable_name": "has_tryit_url"}, "position": {"x": 600, "y": 350}},
            
            # 10. 截图并结束
            {"id": "n17", "type": NodeType.SCREENSHOT, "label": "最终截图", "params": {"name": "runoob_tutorial_test", "full_page": False}, "position": {"x": 600, "y": 450}},
            {"id": "n18", "type": NodeType.END, "label": "结束", "params": {}, "position": {"x": 600, "y": 550}}
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4"},
            {"id": "e4", "source": "n4", "target": "n5"},
            {"id": "e5", "source": "n5", "target": "n6"},
            {"id": "e6", "source": "n6", "target": "n7"},
            {"id": "e7", "source": "n7", "target": "n8"},
            {"id": "e8", "source": "n8", "target": "n9"},
            {"id": "e9", "source": "n9", "target": "n10"},
            {"id": "e10", "source": "n10", "target": "n11"},
            {"id": "e11", "source": "n11", "target": "n12"},
            {"id": "e12", "source": "n12", "target": "n13"},
            {"id": "e13", "source": "n13", "target": "n14"},
            {"id": "e14", "source": "n14", "target": "n15"},
            
            # IF 分支
            {"id": "e15_true", "source": "n15", "target": "n16", "condition_index": 0},
            {"id": "e15_false", "source": "n15", "target": "n17", "condition_index": 1},
            
            {"id": "e16", "source": "n16", "target": "n17"},
            {"id": "e17", "source": "n17", "target": "n18"}
        ],
        "variables": {},
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # 案例 5: 代理与高级请求头测试 (IP查询)
    ip_workflow = {
        "name": "网络配置与属性提取测试",
        "description": "测试自定义 Headers，提取图片 src 和 a 标签 href",
        "nodes": [
            {"id": "n1", "type": NodeType.START, "label": "开始", "params": {
                "engine": "playwright",
                "headers": json.dumps({"Accept-Language": "en-US,en;q=0.9"})
            }, "position": {"x": 200, "y": 50}},
            {"id": "n2", "type": NodeType.GOTO, "label": "访问Httpbin", "params": {"url": "https://httpbin.org/headers", "wait_until": "networkidle", "timeout": 10000}, "position": {"x": 200, "y": 150}},
            {"id": "n3", "type": NodeType.EXTRACT, "label": "提取Headers响应", "params": {"selector": "pre", "variable_name": "response_headers", "selector_type": "css"}, "position": {"x": 200, "y": 250}},
            {"id": "n4", "type": NodeType.GOTO, "label": "访问百度Logo", "params": {"url": "https://www.baidu.com", "wait_until": "domcontentloaded"}, "position": {"x": 200, "y": 350}},
            {"id": "n5", "type": NodeType.EXTRACT, "label": "提取Logo Src", "params": {"selector": "#s_lg_img", "attribute": "src", "variable_name": "logo_src", "selector_type": "css"}, "position": {"x": 200, "y": 450}},
            {"id": "n6", "type": NodeType.EXTRACT, "label": "提取新闻链接", "params": {"selector": "a:has-text('新闻')", "attribute": "href", "variable_name": "news_link", "selector_type": "css"}, "position": {"x": 200, "y": 550}},
            {"id": "n7", "type": NodeType.SCREENSHOT, "label": "结果截图", "params": {"name": "attr_test", "full_page": True}, "position": {"x": 200, "y": 650}},
            {"id": "n8", "type": NodeType.END, "label": "结束", "params": {}, "position": {"x": 200, "y": 750}}
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4"},
            {"id": "e4", "source": "n4", "target": "n5"},
            {"id": "e5", "source": "n5", "target": "n6"},
            {"id": "e6", "source": "n6", "target": "n7"},
            {"id": "e7", "source": "n7", "target": "n8"}
        ],
        "variables": {},
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    mongo.db.workflows.insert_many([runoob_workflow, ip_workflow])
    print("Successfully created ultimate test workflows!")

if __name__ == "__main__":
    create_ultimate_workflows()
