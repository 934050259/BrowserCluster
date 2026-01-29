# 功能更新说明

## 新增功能

### 1. 代理支持

现在支持通过代理服务器访问目标网站，适用于：
- 访问海外网站
- 匿名访问
- 绕过地域限制

#### 使用方法

在 `params` 中添加 `proxy` 配置：

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/scrape",
    json={
        "url": "https://example.com",
        "params": {
            "proxy": {
                "server": "http://proxy.example.com:8080",
                "username": "your_username",  # 可选
                "password": "your_password"   # 可选
            },
            "wait_for": "networkidle",
            "wait_time": 3000
        }
    }
)
```

#### 支持的代理类型

- **HTTP 代理**: `http://proxy.example.com:8080`
- **HTTPS 代理**: `https://proxy.example.com:8443`
- **SOCKS5 代理**: `socks5://proxy.example.com:1080`

#### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| server | string | 是 | 代理服务器地址 |
| username | string | 否 | 代理用户名（如需认证） |
| password | string | 否 | 代理密码（如需认证） |

---

### 2. 接口拦截功能

支持拦截网页加载过程中的 API 请求，获取接口响应数据。

#### 使用方法

在 `params` 中添加 `intercept_apis` 配置：

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/scrape/async",
    json={
        "url": "https://example.com",
        "params": {
            "intercept_apis": [
                "https://api.example.com/*",
                "*/data/user/*",
                "https://example.com/api/v1/products"
            ],
            "wait_time": 5000  # 等待接口加载
        }
    }
)

task_id = response.json()["task_id"]

# 查询任务结果
task = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}").json()

if task["status"] == "success":
    intercepted = task["result"]["intercepted_apis"]
    # intercepted 包含所有拦截到的接口数据
    for pattern, apis in intercepted.items():
        print(f"模式: {pattern}")
        for api in apis:
            print(f"  URL: {api['url']}")
            print(f"  方法: {api['method']}")
            print(f"  状态: {api['status']}")
            print(f"  数据: {api['body']}")
```

#### URL 模式匹配

支持通配符 `*` 进行模糊匹配：

| 模式 | 匹配示例 |
|------|---------|
| `https://api.example.com/*` | `https://api.example.com/users`, `https://api.example.com/products` |
| `*/api/v1/*` | `https://example.com/api/v1/users`, `https://api.com/api/v1/data` |
| `https://example.com/api/users` | `https://example.com/api/users` (精确匹配） |
| `*.json` | `https://example.com/data.json`, `https://api.com/info.json` |

#### 返回数据结构

拦截到的接口数据包含在返回结果的 `intercepted_apis` 字段中：

```json
{
    "status": "success",
    "html": "<html>...</html>",
    "intercepted_apis": {
        "https://api.example.com/*": [
            {
                "url": "https://api.example.com/users",
                "method": "GET",
                "status": 200,
                "headers": {
                    "content-type": "application/json",
                    "content-length": "1234"
                },
                "body": {
                    "users": [...]
                }
            }
        ]
    }
}
```

---

## 完整示例

### 示例 1: 使用代理抓取

```python
import requests

# HTTP 代理
response = requests.post(
    "http://localhost:8000/api/v1/scrape",
    json={
        "url": "https://example.com",
        "params": {
            "proxy": {
                "server": "http://proxy.example.com:8080",
                "username": "user123",
                "password": "pass123"
            },
            "wait_for": "networkidle",
            "wait_time": 3000,
            "block_images": True  # 可选：拦截图片加快速度
        },
        "cache": {
            "enabled": False  # 代理模式下建议禁用缓存
        }
    }
)

result = response.json()
print(f"状态: {result['status']}")
```

### 示例 2: 拦截接口数据

```python
import requests
import time

# 发起异步抓取请求
response = requests.post(
    "http://localhost:8000/api/v1/scrape/async",
    json={
        "url": "https://example.com",
        "params": {
            "intercept_apis": [
                "https://api.example.com/*",
                "*/api/v1/users/*",
                "*.json"
            ],
            "wait_time": 5000
        }
    }
)

task_id = response.json()["task_id"]

# 等待任务完成
while True:
    task = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}").json()
    if task["status"] in ["success", "failed"]:
        break
    time.sleep(1)

# 获取拦截的接口数据
if task["status"] == "success":
    intercepted = task["result"].get("intercepted_apis", {})

    print(f"拦截到 {len(intercepted)} 个接口模式:")
    for pattern, apis in intercepted.items():
        print(f"\n模式: {pattern}")
        print(f"请求数: {len(apis)}")

        for api in apis[:3]:  # 只显示前3个
            print(f"\n  URL: {api['url']}")
            print(f"  方法: {api['method']}")
            print(f"  状态: {api['status']}")
            if isinstance(api.get('body'), dict):
                print(f"  数据: {json.dumps(api['body'], indent=6, ensure_ascii=False)}")
```

### 示例 3: 代理 + 接口拦截

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/scrape/async",
    json={
        "url": "https://example.com",
        "params": {
            # 代理配置
            "proxy": {
                "server": "socks5://proxy.example.com:1080"
            },
            # 接口拦截
            "intercept_apis": [
                "https://api.example.com/*"
            ],
            # 其他参数
            "wait_for": "networkidle",
            "wait_time": 5000,
            "block_images": True,
            "block_media": True,
            "viewport": {
                "width": 1920,
                "height": 1080
            }
        },
        "cache": {
            "enabled": False
        }
    }
)

task_id = response.json()["task_id"]
# ... 查询任务结果
```

---

## 应用场景

### 场景 1: 访问海外网站

通过海外代理访问受地域限制的网站：

```python
{
    "proxy": {
        "server": "http://us-proxy.example.com:8080"
    }
}
```

### 场景 2: 监控 API 调用

拦截并分析网页的 API 请求：

```python
{
    "intercept_apis": [
        "https://www.example.com/api/*",
        "*/api/v1/products"
    ]
}
```

### 场景 3: 获取动态数据

直接获取 API 返回的 JSON 数据，无需解析 HTML：

```python
{
    "intercept_apis": ["https://www.example.com/api/data"]
}

# 返回的接口数据就是结构化的 JSON
```

### 场景 4: 匿名访问 + 数据获取

通过代理匿名访问网站并获取接口数据：

```python
{
    "proxy": {
        "server": "socks5://anonymous-proxy.com:1080"
    },
    "intercept_apis": ["*/api/private/*"]
}
```

---

## 注意事项

1. **代理服务器**
   - 需要有效的代理服务器才能使用代理功能
   - 代理认证信息会安全地传递给 Playwright

2. **接口拦截**
   - 大量拦截可能影响性能，请按需配置
   - 接口拦截不会阻止页面正常加载
   - JSON 响应会自动解析为 Python 字典
   - 非 JSON 响应以文本形式返回

3. **缓存**
   - 使用代理时建议禁用缓存（`cache.enabled = False`）
   - 拦截的接口数据不会缓存

4. **并发**
   - 每个任务会创建独立的浏览器上下文
   - 代理配置不会在不同任务间共享

---

## 示例代码

详细的示例代码请参考：
- `scripts/example.py` - 基础 API 使用示例
- `scripts/example_advanced.py` - 代理和接口拦截高级示例

---

## API 参数更新

### ScrapeParams 模型新增字段

```python
class ScrapeParams(BaseModel):
    # ... 原有字段 ...
    
    proxy: Optional[Dict[str, Any]] = None              # 代理配置
    intercept_apis: Optional[List[str]] = None          # 接口拦截列表
```

### ScrapedResult 模型新增字段

```python
class ScrapedResult(BaseModel):
    # ... 原有字段 ...
    
    intercepted_apis: Optional[Dict[str, Any]] = None   # 拦截的接口数据
```

---

## 更新日志

### v1.1.0 (2024-01-27)
- ✅ 新增代理支持功能
- ✅ 新增接口拦截功能
- ✅ 支持通配符匹配接口 URL
- ✅ 支持多种代理类型（HTTP/HTTPS/SOCKS5）
- ✅ 支持代理认证
- ✅ 拦截数据包含完整响应信息
- ✅ 自动解析 JSON 响应
