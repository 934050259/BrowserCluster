import asyncio
import logging
import sys
import threading
from typing import Dict, List, Optional
from datetime import datetime
from app.core.config import settings
from app.core.logger import setup_node_logger
from app.services.worker import Worker
from app.db.mongo import mongo

logger = logging.getLogger(__name__)

class NodeManager:
    """节点管理器：负责管理 Worker 实例的生命周期和状态同步"""
    
    def __init__(self):
        self.active_workers: Dict[str, Worker] = {}
        self.worker_threads: Dict[str, threading.Thread] = {}

    def _run_worker_thread(self, worker: Worker):
        """在独立线程中运行 Worker，并配置专用的事件循环"""
        # 为新线程创建并设置事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            # 重新创建一个 Proactor 类型的循环以确保策略生效
            loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
            asyncio.set_event_loop(loop)

        # 初始化节点特定的日志记录
        setup_node_logger(worker.node_id)

        logger.info(f"Worker thread for {worker.node_id} started with loop: {type(loop).__name__}")
        
        try:
            loop.run_until_complete(self._run_worker_safe(worker))
        finally:
            loop.close()
            logger.info(f"Worker thread for {worker.node_id} closed")

    async def get_all_nodes(self) -> List[dict]:
        """获取所有节点信息"""
        try:
            # 确保连接已建立
            mongo.connect()
            # 仅查询未被逻辑删除的节点
            cursor = mongo.nodes.find({"is_deleted": {"$ne": True}})
            nodes = []
            now = datetime.now()
            heartbeat_timeout = settings.heartbeat_interval * 2
            
            # 将 cursor 转换为列表以避免在迭代时出现可能的阻塞或连接问题
            for doc in list(cursor):
                if not doc:
                    continue
                doc['_id'] = str(doc['_id'])
                # 确保 node_id 存在，防止 KeyError
                node_id = doc.get('node_id')
                if not node_id:
                    continue
                
                # 检查实时状态
                is_active_locally = node_id in self.active_workers
                db_status = doc.get('status', 'stopped')
                last_seen = doc.get('last_seen')
                
                # 优先级判断逻辑：
                # 1. 如果数据库状态明确为 stopped，则直接返回 stopped
                if db_status == 'stopped':
                    status = 'stopped'
                # 2. 如果在本地活跃列表中，则是 running
                elif is_active_locally:
                    status = 'running'
                # 3. 如果有近期的心跳更新，则是 running
                elif last_seen and (now - last_seen).total_seconds() < heartbeat_timeout:
                    status = 'running'
                # 4. 如果数据库状态是 running 但没有心跳且不在本地活跃，则是 offline
                elif db_status == 'running':
                    status = 'offline'
                else:
                    status = db_status
                
                doc['status'] = status
                
                # 统计任务数量
                try:
                    task_count = mongo.tasks.count_documents({"node_id": node_id})
                    doc['task_count'] = task_count
                except:
                    doc['task_count'] = 0

                # 确保时间字段格式正确且存在
                if 'created_at' not in doc:
                    doc['created_at'] = datetime.now()
                # 确保 max_concurrent 是整数
                if 'max_concurrent' in doc:
                    doc['max_concurrent'] = int(doc['max_concurrent'])
                else:
                    doc['max_concurrent'] = 1
                
                nodes.append(doc)
            return nodes
        except Exception as e:
            logger.error(f"Error getting all nodes: {e}", exc_info=True)
            return []

    async def add_node(self, node_id: str, queue_name: str = "task_queue", max_concurrent: int = 1):
        """添加新节点配置"""
        # 检查是否存在同名且未删除的节点
        existing = mongo.nodes.find_one({"node_id": node_id, "is_deleted": {"$ne": True}})
        if existing:
            raise ValueError(f"Node with ID '{node_id}' already exists.")

        node_data = {
            "node_id": node_id,
            "queue_name": queue_name,
            "max_concurrent": max_concurrent,
            "status": "stopped",
            "retry_count": 0,  # 新增：重试次数
            "is_deleted": False,
            "created_at": datetime.now(),
            "last_seen": None
        }
        mongo.nodes.update_one(
            {"node_id": node_id},
            {"$set": node_data},
            upsert=True
        )
        return node_data

    async def start_node(self, node_id: str) -> bool:
        """启动指定节点"""
        doc = mongo.nodes.find_one({"node_id": node_id})
        if not doc:
            return False
        
        if node_id not in self.active_workers:
            # 创建新的 Worker 实例
            worker = Worker(node_id=node_id)
            self.active_workers[node_id] = worker
            
            # 在独立线程中启动 Worker
            thread = threading.Thread(
                target=self._run_worker_thread,
                args=(worker,),
                name=f"WorkerThread-{node_id}",
                daemon=True
            )
            self.worker_threads[node_id] = thread
            thread.start()
            
            logger.info(f"Node {node_id} thread dispatched")
        
        mongo.nodes.update_one(
            {"node_id": node_id},
            {"$set": {"status": "running", "last_seen": datetime.now(), "retry_count": 0}}
        )
        return True

    async def _run_worker_safe(self, worker: Worker):
        """安全运行 Worker，处理可能的异常"""
        try:
            await worker.run()
        except Exception as e:
            logger.error(f"Worker {worker.node_id} crashed with error: {str(e)}", exc_info=True)
        finally:
            self.active_workers.pop(worker.node_id, None)
            self.worker_threads.pop(worker.node_id, None)
            mongo.nodes.update_one(
                {"node_id": worker.node_id},
                {"$set": {"status": "stopped"}}
            )

    async def stop_node(self, node_id: str) -> bool:
        """停止指定节点"""
        logger.info(f"Attempting to stop node: {node_id}")
        
        # 无论内存中是否存在，都先尝试在数据库中标记停止，防止状态同步问题
        try:
            mongo.nodes.update_one(
                {"node_id": node_id},
                {"$set": {"status": "stopped"}}
            )
        except Exception as e:
            logger.error(f"Database update failed for stop_node {node_id}: {e}")

        if node_id in self.active_workers:
            worker = self.active_workers[node_id]
            # 设置运行标志为 False，Worker 循环会自动退出
            worker.is_running = False
            logger.info(f"Set is_running=False for worker {node_id}")
            
            # 等待一小段时间让线程尝试退出，但不阻塞主循环
            # 我们不在这里 join 线程，因为这可能导致 FastAPI 挂起
            # 相反，我们依赖 _run_worker_safe 里的 finally 块来清理 active_workers
            
            # 注意：不再立即 pop，让线程自己清理，这样可以确保 _run_worker_safe 的 finally 能执行
            logger.info(f"Stop signal sent to worker {node_id}")
        else:
            logger.warning(f"Node {node_id} not found in active_workers")
        
        return True

    async def stop_all_nodes(self):
        """停止所有正在运行的节点"""
        logger.info("Stopping all active nodes...")
        node_ids = list(self.active_workers.keys())
        for node_id in node_ids:
            await self.stop_node(node_id)
        
        # 等待一段时间让 worker 线程有时间清理资源
        if node_ids:
            logger.info(f"Waiting for {len(node_ids)} workers to shut down...")
            await asyncio.sleep(2)
        
        return True

    async def delete_node(self, node_id: str) -> bool:
        """逻辑删除节点配置及实例"""
        await self.stop_node(node_id)
        mongo.nodes.update_one(
            {"node_id": node_id},
            {"$set": {"is_deleted": True, "status": "stopped"}}
        )
        return True

    async def update_node(self, node_id: str, update_data: dict) -> bool:
        """更新节点配置"""
        # 如果节点正在运行，可能需要重启
        is_running = node_id in self.active_workers
        
        mongo.nodes.update_one(
            {"node_id": node_id},
            {"$set": update_data}
        )
        
        if is_running:
            await self.stop_node(node_id)
            await self.start_node(node_id)
            
        return True

    async def auto_start_nodes(self):
        """系统启动时，自动启动数据库中状态为 running 的节点"""
        try:
            mongo.connect()
            # 查找所有状态为 running 且未删除的节点
            cursor = mongo.nodes.find({"status": "running", "is_deleted": {"$ne": True}})
            nodes = list(cursor)
            
            if not nodes:
                logger.info("No nodes to auto-start.")
                return

            logger.info(f"Found {len(nodes)} nodes to auto-start.")
            for doc in nodes:
                node_id = doc.get("node_id")
                if node_id:
                    # 如果已经在运行中，则跳过
                    if node_id in self.active_workers:
                        continue
                    
                    # 检查重试次数，避免无限重启
                    retry_count = doc.get("retry_count", 0)
                    if retry_count >= settings.max_node_auto_retries:
                        logger.warning(f"Node {node_id} exceeded max auto-start retries ({retry_count}). Marking as stopped.")
                        mongo.nodes.update_one(
                            {"node_id": node_id},
                            {"$set": {"status": "stopped", "retry_count": 0}}
                        )
                        continue
                        
                    logger.info(f"Auto-starting node: {node_id} (Retry count: {retry_count})")
                    
                    # 增加重试计数
                    mongo.nodes.update_one(
                        {"node_id": node_id},
                        {"$inc": {"retry_count": 1}}
                    )
                    
                    # 调用 start_node 会创建 Worker 并在独立线程中运行
                    await self.start_node(node_id)
        except Exception as e:
            logger.error(f"Error during auto-starting nodes: {e}", exc_info=True)

# 全局单例
node_manager = NodeManager()
