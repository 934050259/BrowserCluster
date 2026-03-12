"""
RabbitMQ 消息队列服务模块

提供任务发布和消费功能
"""
import pika
import json
import logging
import threading
import time
import socket
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
        # 增加更严格的存活检查，如果连接虽然没关闭但已不可用（如由于心跳超时），也重新连接
        is_unhealthy = False
        if self._connection and not self._connection.is_closed:
            try:
                # 尝试调用 process_data_events 来验证连接活性
                # 如果连接已经静默断开，这里通常会触发异常
                self._connection.process_data_events(time_limit=0)
            except Exception as e:
                logger.warning(f"RabbitMQ existing connection health check failed: {e}")
                is_unhealthy = True
                self.close() # 彻底清理旧连接

        if self._connection is None or self._connection.is_closed or is_unhealthy:
            try:
                # 彻底重构参数解析逻辑，改用 ConnectionParameters 以支持 TCP Keepalive
                # URLParameters 在某些版本中是不可变的或限制了属性设置，容易导致 AttributeError
                url_p = pika.URLParameters(settings.rabbitmq_url)
                
                # 创建显式的 ConnectionParameters
                # 注意：某些版本的 pika 不支持在构造函数中直接传入 socket_options
                params = pika.ConnectionParameters(
                    host=url_p.host,
                    port=url_p.port,
                    virtual_host=url_p.virtual_host,
                    credentials=url_p.credentials,
                    heartbeat=settings.rabbitmq_heartbeat,
                    blocked_connection_timeout=settings.rabbitmq_blocked_timeout,
                    socket_timeout=10
                )
                
                # 显式设置底层 socket 选项 (level, optname, value)
                # SO_KEEPALIVE = 1 启用心跳，防止网络设备在空闲时静默关闭连接
                try:
                    # 优先检查是否存在 socket_options 属性
                    if hasattr(params, 'socket_options'):
                        params.socket_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
                    else:
                        logger.warning("pika.ConnectionParameters does not have 'socket_options' attribute")
                except Exception as e:
                    logger.warning(f"Could not set socket_options on pika params: {e}")
                
                # 创建连接
                connection_info = settings.rabbitmq_url.split('@')[-1]
                logger.info(f"Attempting to connect to RabbitMQ: {connection_info} (heartbeat={settings.rabbitmq_heartbeat}s)")
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                logger.info(f"Successfully established RabbitMQ connection and channel")

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
                logger.info(f"RabbitMQ connection and queue '{settings.rabbitmq_queue}' are ready")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self.close() # 清理残留
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
            logger.info(f"Published task {task.get('task_id')} to queue '{settings.rabbitmq_queue}'")
            return True
        except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError, 
                pika.exceptions.AMQPConnectionError, ConnectionResetError, OSError) as e:
            logger.warning(f"RabbitMQ connection lost during publish: {e}")
            # 彻底清理旧连接，强制下次 connect() 重新创建
            self.close()
            if retry:
                logger.info("Retrying publish task with fresh connection...")
                # 等待 1 秒再重试，给 RabbitMQ 一点反应时间
                time.sleep(1)
                return self.publish_task(task, retry=False)
            return False
        except Exception as e:
            logger.error(f"Failed to publish task due to unexpected error: {e}")
            self.close()
            return False

    def consume_tasks(
        self,
        callback: Callable[[Dict[str, Any], Any, Any], None],
        prefetch_count: int = 1,
        should_stop: Callable[[], bool] = None
    ):
        """
        开始消费队列中的任务
        """
        while True:
            if should_stop and should_stop():
                logger.info("Consumer loop stopping: received stop signal")
                break

            channel = None
            try:
                channel = self.connect()
                channel.basic_qos(prefetch_count=prefetch_count)

                def wrapper(ch, method, properties, body):
                    """消息处理包装函数"""
                    try:
                        task = json.loads(body)
                        task_id = task.get("task_id", "unknown")
                        logger.info(f"Consumer received task {task_id}")
                        # 将 channel 和 method 传递给回调，由回调负责 ack
                        callback(task, ch, method)
                    except Exception as e:
                        logger.error(f"Error processing task wrapper: {e}")
                        try:
                            # 解析错误等严重问题，直接 nack
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        except:
                            pass

                consumer_tag = channel.basic_consume(
                    queue=settings.rabbitmq_queue,
                    on_message_callback=wrapper,
                    auto_ack=False  # 显式关闭自动确认
                )

                logger.info(f"Consumer registered (tag: {consumer_tag}). Waiting for tasks...")
                
                last_heartbeat_log = time.time()
                while True:
                    if should_stop and should_stop():
                        logger.info("Consumer inner loop: detected stop signal, exiting...")
                        return
                    
                    # 检查连接健康
                    if self._connection is None or self._connection.is_closed:
                        logger.warning("Connection lost in consumer inner loop, breaking to reconnect...")
                        break
                    
                    # 每 5 分钟打印一次活跃日志
                    if time.time() - last_heartbeat_log > 300:
                        logger.info("RabbitMQ consumer is alive and waiting for messages...")
                        last_heartbeat_log = time.time()

                    try:
                        # 定期轮询事件（包括心跳和消息投递）
                        self._connection.process_data_events(time_limit=1.0)
                    except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError, 
                            pika.exceptions.AMQPConnectionError, ConnectionResetError, OSError) as e:
                        logger.warning(f"RabbitMQ connection lost during consumption: {e}. Reconnecting...")
                        self.close()
                        break # 跳出内层循环，进入外层循环重连
                    except Exception as e:
                        logger.error(f"Unexpected error in consumer thread: {e}")
                        # 记录错误并等待，防止在极端情况下疯狂刷日志
                        time.sleep(2)
                        # 尝试通过主动探测来恢复或触发连接断开
                        try:
                            if self._connection and not self._connection.is_closed:
                                self._connection.process_data_events(time_limit=0)
                            else:
                                break
                        except:
                            self.close()
                            break
                
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.ConnectionClosed, 
                    ConnectionResetError, OSError) as e:
                logger.error(f"RabbitMQ consumer connection failed: {e}. Retrying in 5 seconds...")
                self.close()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Critical error in consumer thread: {e}")
                self.close()
                time.sleep(5)
            finally:
                # 确保在异常发生时也关闭当前连接，防止句柄泄露
                self.close()

    def ack_message(self, channel, delivery_tag):
        """线程安全地确认消息"""
        if channel and not channel.is_closed:
            try:
                conn = channel.connection
                if conn and not conn.is_closed:
                    conn.add_callback_threadsafe(
                        lambda: channel.basic_ack(delivery_tag=delivery_tag)
                    )
            except Exception as e:
                logger.error(f"Failed to schedule basic_ack: {e}")

    def nack_message(self, channel, delivery_tag, requeue=True):
        """线程安全地拒绝消息"""
        if channel and not channel.is_closed:
            try:
                conn = channel.connection
                if conn and not conn.is_closed:
                    conn.add_callback_threadsafe(
                        lambda: channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
                    )
            except Exception as e:
                logger.error(f"Failed to schedule basic_nack: {e}")

    def close(self):
        """关闭 RabbitMQ 连接"""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
        except Exception:
            pass
            
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass
            
        self._channel = None
        self._connection = None


# 全局 RabbitMQ 服务实例
rabbitmq_service = RabbitMQService()
