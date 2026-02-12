"""
RabbitMQ 消息队列服务模块

提供任务发布和消费功能
"""
import pika
import json
import logging
import threading
import time
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
        except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError, 
                pika.exceptions.AMQPConnectionError, ConnectionResetError, OSError) as e:
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
        """
        while True:
            if should_stop and should_stop():
                break

            channel = None
            try:
                channel = self.connect()
                channel.basic_qos(prefetch_count=prefetch_count)

                def wrapper(ch, method, properties, body):
                    """消息处理包装函数"""
                    try:
                        task = json.loads(body)
                        callback(task)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"Error processing task: {e}")
                        try:
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        except:
                            pass

                channel.basic_consume(
                    queue=settings.rabbitmq_queue,
                    on_message_callback=wrapper
                )

                logger.info("Started consuming tasks...")
                
                while True:
                    if should_stop and should_stop():
                        logger.info("Consumer loop: detected stop signal, exiting...")
                        return
                    
                    try:
                        self._connection.process_data_events(time_limit=0.5)
                    except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError, 
                            pika.exceptions.AMQPConnectionError, ConnectionResetError, OSError) as e:
                        logger.warning(f"RabbitMQ connection lost during consumption: {e}. Attempting to reconnect...")
                        self._connection = None
                        self._channel = None
                        break # 跳出内层循环，进入外层循环重连
                    except Exception as e:
                        logger.error(f"Unexpected error in process_data_events: {e}")
                        # 对于非连接错误，记录并稍后重试，避免进程崩溃
                        time.sleep(1)
                
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.ConnectionClosed, 
                    ConnectionResetError, OSError) as e:
                logger.error(f"RabbitMQ connection error: {e}. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in consumer: {e}")
                time.sleep(5)
            finally:
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
