import asyncio
import httpx
import time
import sys
from typing import List, Dict, Any

# 默认基础 URL，可根据实际情况修改
BASE_URL = "http://localhost:8000/api/v1"

async def test_single_task_sync():
    """测试同步单任务推送与结果获取"""
    print("\n=== Testing Single Task (Sync) ===")
    url = f"{BASE_URL}/scrape"
    payload = {
        "url": "https://example.com",
        "params": {
            "wait_for": "domcontentloaded",
            "timeout": 10000,
            "screenshot": False
        },
        "cache": {"enabled": False}  # 禁用缓存以确保每次都执行
    }
    
    async with httpx.AsyncClient() as client:
        print(f"Sending POST request to {url}...")
        start_time = time.time()
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return

            data = response.json()
            duration = time.time() - start_time
            
            print(f"Task completed in {duration:.2f}s")
            print(f"Task ID: {data.get('task_id')}")
            print(f"Status: {data.get('status')}")
            
            # 验证结果
            if data.get("status") == "success":
                print("Result verification: SUCCESS")
                print("Result snippet:", data.get('result', {}).get('metadata'))
            else:
                print("Result verification: FAILED")
                
        except httpx.HTTPError as e:
            print(f"Request failed: {e}")

async def test_single_task_async():
    """测试异步单任务推送与轮询结果"""
    print("\n=== Testing Single Task (Async) ===")
    push_url = f"{BASE_URL}/scrape/async"
    payload = {
        "url": "https://example.com",
        "priority": 2,
        "params": {"wait_for": "domcontentloaded"},
        "cache": {"enabled": False}
    }
    
    async with httpx.AsyncClient() as client:
        # 1. 推送任务
        print(f"Pushing task to {push_url}...")
        try:
            resp = await client.post(push_url, json=payload)
            if resp.status_code != 200:
                print(f"Push failed: {resp.status_code} - {resp.text}")
                return
                
            task_data = resp.json()
            task_id = task_data["task_id"]
            print(f"Task pushed. ID: {task_id}")
            
            # 2. 轮询结果
            await poll_task_result(client, task_id)
            
        except httpx.HTTPError as e:
            print(f"Request failed: {e}")

async def test_batch_tasks():
    """测试批量任务推送与并发轮询结果"""
    print("\n=== Testing Batch Tasks ===")
    batch_url = f"{BASE_URL}/scrape/batch"
    
    # 构建批量请求
    payload = {
        "tasks": [
            {
                "url": "https://myip.ipip.net/",
                "params": {
                    "engine": "drissionpage",
                    "proxy": {
                    "server": "http://223.111.202.92:20198",
                    },
                    "save_html": False,
                    "screenshot": True,
                },
                "cache": {
                    "enabled": False,
                    "ttl": 3600
                },
                "priority": 1
            },
            {
                "url": "https://myip.ipip.net/",
                "params": {
                    "proxy": {
                    "server": "http://223.111.202.93:20106",
                    },
                    "save_html": False,
                    "screenshot": True,
                },
                "cache": {
                    "enabled": False,
                    "ttl": 3600
                },
                "priority": 1
            },
            {
                "url": "https://myip.ipip.net/",
                "params": {
                    "proxy": {
                    "server": "http://223.111.202.95:20016",
                    },
                    "save_html": False,
                    "screenshot": True,
                },
                "cache": {
                    "enabled": False,
                    "ttl": 3600
                },
                "priority": 1
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        # 1. 推送批量任务
        print(f"Pushing batch tasks to {batch_url}...")
        try:
            resp = await client.post(batch_url, json=payload)
            if resp.status_code != 200:
                print(f"Batch push failed: {resp.status_code} - {resp.text}")
                return

            data = resp.json()
            task_ids = data["task_ids"]
            print(f"Batch pushed. Task IDs: {task_ids}")
            print(f"Waiting for {len(task_ids)} tasks to complete...")
            
            # 2. 并发轮询所有结果
            # 使用 asyncio.gather 同时等待所有任务完成
            tasks = [poll_task_result(client, tid) for tid in task_ids]
            results = await asyncio.gather(*tasks)
            
            # 统计结果
            success_count = sum(1 for r in results if r and r.get("status") == "success")
            print(f"\nBatch Summary: {success_count}/{len(task_ids)} tasks succeeded")
            
        except httpx.HTTPError as e:
            print(f"Request failed: {e}")

async def poll_task_result(client: httpx.AsyncClient, task_id: str, max_retries=60, interval=1.0):
    """轮询任务结果辅助函数"""
    url = f"{BASE_URL}/tasks/{task_id}"
    # print(f"Starting polling for task {task_id}...")
    
    for i in range(max_retries):
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                print(f"[Task {task_id}] Not found yet...")
                await asyncio.sleep(interval)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            
            if status in ["success", "failed"]:
                print(f"[Task {task_id}] Finished with status: {status}")
                return data
            
            # 每 5 次打印一次进度，避免刷屏
            if i % 5 == 0:
                print(f"[Task {task_id}] Status: {status} (Waited {i*interval}s)")
            
            await asyncio.sleep(interval)
            
        except Exception as e:
            print(f"[Task {task_id}] Polling error: {e}")
            await asyncio.sleep(interval)
            
    print(f"[Task {task_id}] Timeout after {max_retries} attempts")
    return None

async def main():
    print("Checking server status...")
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE_URL.replace('/api/v1', '/health')}")
            print("Server is UP.")
        except Exception as e:
            print(f"Error: Server is not running at {BASE_URL.split('/api')[0]}")
            print("Please start the backend server first.")
            return

    # await test_single_task_sync()
    # await test_single_task_async()
    await test_batch_tasks()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTests stopped by user.")
