from app.db.mongo import mongo
from datetime import datetime

def fix_sample():
    mongo.connect()
    
    updated_nodes = [
        {'id': 'start-1', 'type': 'start', 'label': '开始', 'position': {'x': 250, 'y': 50}, 'params': {}},
        {'id': 'goto-1', 'type': 'goto', 'label': '打开百度', 'position': {'x': 250, 'y': 150}, 'params': {'url': 'https://www.baidu.com', 'wait_until': 'networkidle'}},
        {'id': 'type-1', 'type': 'type', 'label': '输入搜索词', 'position': {'x': 250, 'y': 250}, 'params': {'selector': '#kw', 'value': 'Playwright 自动化测试', 'selector_type': 'css'}},
        {'id': 'click-1', 'type': 'click', 'label': '点击搜索', 'position': {'x': 250, 'y': 350}, 'params': {'selector': '#su', 'selector_type': 'css'}},
        {'id': 'wait-1', 'type': 'wait', 'label': '等待结果', 'position': {'x': 250, 'y': 450}, 'params': {'selector': '#content_left', 'timeout': 5000, 'selector_type': 'css'}},
        {'id': 'extract-1', 'type': 'extract', 'label': '提取首条标题', 'position': {'x': 250, 'y': 550}, 'params': {'selector': 'h3.t', 'variable_name': 'first_result_title', 'selector_type': 'css'}},
        {'id': 'screenshot-1', 'type': 'screenshot', 'label': '结果截图', 'position': {'x': 250, 'y': 650}, 'params': {'name': 'baidu_search_result'}},
        {'id': 'end-1', 'type': 'end', 'label': '结束', 'position': {'x': 250, 'y': 750}, 'params': {}}
    ]
    
    res = mongo.db.workflows.update_one(
        {'name': '百度搜索示例'}, 
        {'$set': {'nodes': updated_nodes, 'updated_at': datetime.now()}}
    )
    print(f"Sample workflow updated: {res.modified_count} document(s) modified")

if __name__ == "__main__":
    fix_sample()
