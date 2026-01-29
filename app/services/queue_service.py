"""
RabbitMQ 消息队列服务模块

提供任务发布和消费功能
"""
import pika
import json
import logging
import threading
from typing import Dict, Any, Callable
from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQService:
    """RabbitMQ 服务单例类"""

    _instance = None  # 单例实例

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._local = threading.local()
        return cls._instance

    @property
    def _connection(self):
        return getattr(self._local, 'connection', None)

    @_connection.setter
    def _connection(self, value):
        self._local.connection = value

    @property
    def _channel(self):
        return getattr(self._local, 'channel', None)

    @_channel.setter
    def _channel(self, value):
        self._local.channel = value

    def connect(self):
        """
        连接到 RabbitMQ 并初始化交换机和队列

        Returns:
            Channel: RabbitMQ 通道
        """
        if self._connection is None or self._connection.is_closed:
            try:
                # 创建连接
                self._connection = pika.BlockingConnection(
                    pika.URLParameters(settings.rabbitmq_url)
                )
                self._channel = self._connection.channel()

                # 声明交换机
                self._channel.exchange_declare(
                    exchange=settings.rabbitmq_exchange,
                    exchange_type='direct',
                    durable=True
                )

                # 声明队列
                self._channel.queue_declare(
                    queue=settings.rabbitmq_queue,
                    durable=True
                )

                # 绑定队列到交换机
                self._channel.queue_bind(
                    exchange=settings.rabbitmq_exchange,
                    queue=settings.rabbitmq_queue,
                    routing_key=settings.rabbitmq_queue
                )
                logger.info("Successfully connected to RabbitMQ")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self._connection = None
                self._channel = None
                raise

        return self._channel

    def publish_task(self, task: Dict[str, Any], retry: bool = True) -> bool:
        """
        发布任务到队列

        Args:
            task: 任务数据字典
            retry: 失败时是否重试一次

        Returns:
            bool: 是否成功发布
        """
        try:
            channel = self.connect()
            channel.basic_publish(
                exchange=settings.rabbitmq_exchange,
                routing_key=settings.rabbitmq_queue,
                body=json.dumps(task),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 持久化
                    priority=task.get('priority', 1)  # 优先级
                )
            )
            logger.info(f"Published task {task.get('task_id')} to queue")
            return True
        except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError, pika.exceptions.AMQPConnectionError) as e:
            logger.warning(f"RabbitMQ connection lost during publish: {e}")
            self._connection = None
            self._channel = None
            if retry:
                logger.info("Retrying publish task...")
                return self.publish_task(task, retry=False)
            return False
        except Exception as e:
            logger.error(f"Failed to publish task due to unexpected error: {e}")
            return False

    def consume_tasks(
        self,
        callback: Callable[[Dict[str, Any]], None],
        prefetch_count: int = 1,
        should_stop: Callable[[], bool] = None
    ):
        """
        开始消费队列中的任务

        Args:
            callback: 处理任务的回调函数
            prefetch_count: 预取消息数量
            should_stop: 可选的停止判断函数
        """
        channel = None
        try:
            channel = self.connect()
            # 设置预取数量，实现公平分发
            channel.basic_qos(prefetch_count=prefetch_count)

            def wrapper(ch, method, properties, body):
                """消息处理包装函数"""
                try:
                    # 解析任务
                    task = json.loads(body)
                    # 调用回调函数处理任务
                    callback(task)
                    
                    # 注意：由于 callback(task) 内部可能包含异步处理逻辑（如 asyncio.run_coroutine_threadsafe），
                    # 这里立即确认消息可能存在风险（如果任务还没处理完进程就崩溃了）。
                    # 但在当前的 worker.py 实现中，回调函数会将协程提交给事件循环。
                    # 为了确保任务不会因为节点停止而“丢失”且保持 PROCESSING，
                    # 我们在 worker.py 的 stop() 方法中已经添加了重置状态逻辑。
                    
                    # 确认消息已处理
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing task: {e}")
                    # 拒绝消息并重新入队，以便其他节点处理或稍后重试
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )

            # 开始消费消息
            channel.basic_consume(
                queue=settings.rabbitmq_queue,
                on_message_callback=wrapper
            )

            logger.info("Started consuming tasks...")
            
            # 使用循环非阻塞方式消费，以便响应停止信号
            while True:
                if should_stop and should_stop():
                    logger.info("Consumer loop: detected stop signal, exiting...")
                    break
                
                try:
                    # 检查消息，超时时间设为 0.5 秒，更频繁地检查停止信号
                    self._connection.process_data_events(time_limit=0.5)
                except Exception as e:
                    logger.error(f"Error in process_data_events: {e}")
                    break
                
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
        finally:
            # 不要在这里关闭单例的连接，只需停止当前消费
            if channel and not channel.is_closed:
                try:
                    channel.stop_consuming()
                except:
                    pass

    def close(self):
        """关闭 RabbitMQ 连接"""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()
        self._channel = None
        self._connection = None


# 全局 RabbitMQ 服务实例
rabbitmq_service = RabbitMQService()
