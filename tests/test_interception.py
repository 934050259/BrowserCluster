import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def get_token():
    """获取登录 Token"""
    url = f"{BASE_URL}/auth/login"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "username": "admin",
            "password": "admin"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None

async def test_api_interception():
    """测试接口拦截功能"""
    print("\n=== Testing API Interception ===")
    
    token = await get_token()
    if not token:
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/scrape/"
    
    # 尝试访问百度并拦截其搜索建议接口或其他静态资源
    payload = {
        "url": "https://www.baidu.com",
        "params": {
            "intercept_apis": [
                "*/sugrec*",       # 百度搜索建议
                "*/ai_music.png"
            ],
            "intercept_continue": False, # 继续请求，否则页面可能加载不完全
            "screenshot": True,
            "wait_time": 2000,
            "timeout": 20000
        },
        "cache": {"enabled": False}
    }
    
    async with httpx.AsyncClient() as client:
        print(f"Sending request to {url} with interception patterns: {payload['params']['intercept_apis']}")
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return

            data = response.json()
            
            if data.get("status") == "success":
                intercepted = data.get("result", {}).get("intercepted_apis", {})
                print(f"\nInterception Result: SUCCESS")
                print(f"Total patterns matched: {len(intercepted)}")
                
                for pattern, requests in intercepted.items():
                    print(f"\nPattern: {pattern}")
                    print(f"  Captured requests: {len(requests)}")
                    if requests:
                        first = requests[0]
                        print(f"  First request URL: {first['url']}")
                        print(f"  Status: {first['status']}")
                        # print(f"  Body snippet: {str(first.get('body'))[:100]}...")
            else:
                print(f"\nInterception Result: FAILED")
                print(f"Error: {data.get('message')}")
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_interception())
