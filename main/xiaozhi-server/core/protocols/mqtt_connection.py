import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable
from config.logger import setup_logging
from core.utils.mqtt_auth import validate_mqtt_credentials

logger = setup_logging()


class MQTTConnection:
    """
    MQTT连接处理类：管理单个MQTT客户端连接
    处理MQTT协议消息和会话管理
    """

    def __init__(self, socket, connection_id: int, mqtt_server, udp_handler=None, reader=None, writer=None):
        self.socket = socket
        self.reader = reader
        self.writer = writer
        self.connection_id = connection_id
        self.mqtt_server = mqtt_server
        self.udp_handler = udp_handler

        # 连接信息
        self.client_id = None
        self.device_id = None
        self.username = None
        self.password = None
        self.session_id = None

        # 协议状态
        self.is_connected_flag = False
        self.keep_alive_interval = 0
        self.last_activity = time.monotonic()

        # 消息处理
        self.message_callback = None
        self.reply_topic = None

        # UDP相关
        self.udp_config = None
        self.message_queue_size = int(
            getattr(mqtt_server, "message_queue_size", 128) or 128
        )
        self.business_ready_timeout = float(
            getattr(mqtt_server, "business_ready_timeout", 30) or 30
        )
        self.close_timeout = max(
            0.1, float(getattr(mqtt_server, "close_timeout", 2) or 2)
        )
        self.goodbye_timeout = max(
            0.1, float(getattr(mqtt_server, "goodbye_timeout", 1) or 1)
        )

        # 任务管理
        self.keep_alive_task = None
        self.business_task = None
        self._closed = False
        self._close_task = None
        self._close_initiator = None
        self._close_complete = asyncio.Event()
        self.connect_processed_event = asyncio.Event()
        self.connect_accepted = False
        self.business_ready_event = asyncio.Event()
        self._hello_business_ready_event = None
        self._hello_business_session_id = None
        self._logical_hello_received = False
        self._startup_recovery_task = None
        self._session_transition_lock = asyncio.Lock()
        self._last_goodbye_session_id = None
        self._goodbye_lock = asyncio.Lock()

        # 创建MQTT协议处理器
        from core.protocols.mqtt_protocol import MQTTProtocol
        self.protocol = MQTTProtocol(
            socket=socket,
            reader=reader,
            writer=writer,
            max_payload_size=getattr(mqtt_server, "max_payload_size", 8192),
            event_queue_size=self.message_queue_size,
            close_timeout=self.close_timeout,
        )
        self._setup_protocol_handlers()

    def _setup_protocol_handlers(self):
        """设置协议事件处理"""
        self.protocol.on('connect', self._handle_connect)
        self.protocol.on('publish', self._handle_publish)
        self.protocol.on('subscribe', self._handle_subscribe)
        self.protocol.on('disconnect', self._handle_disconnect)
        self.protocol.on('close', self._handle_close)
        self.protocol.on('error', self._handle_error)
        self.protocol.on('protocolError', self._handle_error)
        self.protocol.on('activity', self._handle_activity)

    def _handle_activity(self):
        """更新最近活动时间（用于心跳保活）"""
        self.last_activity = time.monotonic()

    async def _handle_connect(self, connect_data: Dict[str, Any]):
        """处理CONNECT消息"""
        try:
            if self.connect_processed_event.is_set() or self.is_connected_flag:
                logger.warning("同一TCP连接收到重复CONNECT，关闭连接")
                await self.close()
                return
            self.client_id = connect_data['clientId']
            self.username = connect_data.get('username')
            self.password = connect_data.get('password')
            self.keep_alive_interval = connect_data.get('keepAlive', 0) * 1000  # 转换为毫秒

            logger.info(f"MQTT客户端连接: {self.client_id}")

            try:
                validate_mqtt_credentials(
                    self.client_id,
                    self.username,
                    self.password,
                    self.mqtt_server.signature_key,
                )
            except ValueError as e:
                logger.warning(f"MQTT客户端认证失败: {self.client_id}, {e}")
                await self.protocol.send_connack(4)
                self.connect_processed_event.set()
                await self.close()
                return False

            # 解析客户端ID获取设备信息
            if not self._parse_client_id():
                await self.protocol.send_connack(1)  # 连接被拒绝
                self.connect_processed_event.set()
                await self.close()
                return False

            # 生成会话ID
            self.session_id = str(uuid.uuid4())

            # 设置回复主题
            self.reply_topic = f"devices/p2p/{self.device_id.replace(':', '_')}"

            async def complete_acceptance():
                # Keep this inside the server's per-client takeover lock. A
                # newer connection cannot reclaim this clientId between the
                # success CONNACK and publishing the active owner.
                self.is_connected_flag = True
                try:
                    await self.protocol.send_connack(0)
                except Exception:
                    self.is_connected_flag = False
                    raise
                if self.keep_alive_interval > 0:
                    self.keep_alive_task = asyncio.create_task(
                        self._keep_alive_check()
                    )
                self.connect_accepted = True

            accepted = await self.mqtt_server.on_client_connected(
                self, complete_acceptance
            )
            if not accepted:
                if not self._closed:
                    await self.protocol.send_connack(3)  # 服务端暂不可用
                self.connect_processed_event.set()
                await self.close()
                return False
            self.connect_processed_event.set()
            return True

        except Exception as e:
            logger.error(f"处理CONNECT消息失败: {e}")
            self.connect_processed_event.set()
            await self.close()
            return False

    def _parse_client_id(self) -> bool:
        """解析客户端ID获取设备信息"""
        try:
            # 支持格式: GID_test@@@mac_address@@@uuid 或 GID_test@@@mac_address
            parts = self.client_id.split('@@@')

            if len(parts) >= 2:
                self.group_id = parts[0]
                # 将设备标识统一为服务端使用的MAC地址格式
                self.device_id = (
                    parts[1].replace('_', ':').replace('-', ':').lower()
                )

                if len(parts) >= 3:
                    self.uuid = parts[2]

                return True
            else:
                logger.error(f"无效的客户端ID格式: {self.client_id}")
                return False

        except Exception as e:
            logger.error(f"解析客户端ID失败: {e}")
            return False

    async def _handle_publish(self, publish_data: Dict[str, Any]):
        """处理PUBLISH消息"""
        try:
            if publish_data.get('qos', 0) != 0:
                logger.warning(
                    f"不支持的MQTT QoS级别: {publish_data.get('qos')}"
                )
                await self.close()
                return
            topic = publish_data['topic']
            payload = publish_data['payload']

            logger.debug(f"收到MQTT发布消息: topic={topic}, payload={payload}")

            # 更新活动时间
            self.last_activity = time.monotonic()

            # 解析JSON消息
            try:
                message_data = json.loads(payload)

                # 处理不同类型的消息
                if message_data.get('type') == 'hello':
                    if message_data.get('version', 3) != 3:
                        logger.warning(
                            f"不支持的MQTT协议版本: {message_data.get('version')}"
                        )
                        await self.close()
                        return
                    await self._handle_hello_message(message_data)
                else:
                    # 其他消息通过回调处理
                    if self.message_callback:
                        self.message_callback(topic, payload)

            except json.JSONDecodeError:
                logger.error(f"MQTT消息JSON解析失败: {payload}")

        except Exception as e:
            logger.error(f"处理PUBLISH消息失败: {e}")

    async def _handle_hello_message(self, message_data: Dict[str, Any]):
        """处理hello消息，初始化UDP配置"""
        async with self._session_transition_lock:
            self._logical_hello_received = True
        try:
            handle_logical_hello = getattr(
                self.mqtt_server, "handle_logical_hello", None
            )
            if callable(handle_logical_hello):
                await handle_logical_hello(self)
            # Match the gateway contract: do not advertise a usable audio
            # channel until private config and runtime components are ready.
            await asyncio.wait_for(
                self.business_ready_event.wait(),
                timeout=self.business_ready_timeout,
            )
            if self._closed or not self.is_connected_flag:
                return
            hello_reply = self._prepare_hello_reply(
                message_data.get('audio_params', {}),
                message_data.get('version', 3),
            )
            hello_ready = asyncio.Event()
            self._hello_business_ready_event = hello_ready
            self._hello_business_session_id = self.session_id

            # Enqueue the logical-session boundary before the device can react
            # to the reply with UDP audio.
            if self.message_callback:
                try:
                    self.message_callback(self.reply_topic, json.dumps(message_data))
                except Exception as e:
                    logger.error(f"转发hello消息失败: {e}")

            # Long-lived MQTT connections can change Agent configuration at
            # each logical Hello. Do not expose the new UDP session until the
            # business runtime has either refreshed or deliberately retained
            # the previous healthy runtime.
            await asyncio.wait_for(
                hello_ready.wait(),
                timeout=self.business_ready_timeout,
            )
            if self._closed or not self.is_connected_flag:
                return
            await self.send_message(self.reply_topic, json.dumps(hello_reply))

            logger.info(f"MQTT Hello消息处理完成: {self.client_id}")

        except asyncio.TimeoutError:
            logger.error(
                f"MQTT Hello等待业务运行时超时: {self.client_id}, "
                f"timeout={self.business_ready_timeout}s"
            )
            await self.close()
        except Exception as e:
            logger.error(f"处理hello消息失败: {e}")
        finally:
            self._hello_business_ready_event = None
            self._hello_business_session_id = None

    def schedule_stale_session_recovery(self, delay: float = 1.0) -> None:
        """Return a reconnected device with a stale UDP session to Idle."""
        if self._startup_recovery_task is not None:
            return
        self._startup_recovery_task = asyncio.create_task(
            self._recover_stale_session(delay)
        )

    async def _recover_stale_session(self, delay: float) -> None:
        try:
            await asyncio.sleep(max(0.0, delay))
            async with self._session_transition_lock:
                if (
                    self._closed
                    or not self.is_connected_flag
                    or self._logical_hello_received
                    or not self.reply_topic
                ):
                    return
                # No session id is intentional: firmware accepts this as a
                # connection-level reset and discards an UDP session owned by
                # a previous server process. Serialize it with Hello so this
                # reset can never overtake a newly negotiated session.
                await self.send_message(
                    self.reply_topic,
                    json.dumps({"type": "goodbye"}),
                )
                logger.info("已通知重连MQTT设备清理旧UDP会话: {}", self.client_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("通知重连MQTT设备清理旧会话失败: {}", e)

    def mark_business_session_ready(self, session_id: str = None) -> None:
        """Acknowledge readiness for the currently pending logical Hello."""
        event = self._hello_business_ready_event
        pending_session_id = self._hello_business_session_id
        if event is None:
            return
        if session_id is not None and pending_session_id != session_id:
            return
        event.set()

    async def send_hello_reply(self, audio_params: Dict[str, Any], version: int = 3):
        """发送hello回复（可在未收到设备hello时调用）"""
        hello_reply = self._prepare_hello_reply(audio_params, version)
        await self.send_message(self.reply_topic, json.dumps(hello_reply))

    def _prepare_hello_reply(self, audio_params: Dict[str, Any], version: int = 3):
        """Create and install one UDP session without publishing it yet."""
        import os

        self.session_id = str(uuid.uuid4())
        self._last_goodbye_session_id = None
        udp_session_id = self.mqtt_server.bind_udp_session(
            self, self.udp_handler
        )
        nonce = self._generate_udp_header(
            0, 0, 0, connection_id=udp_session_id
        )
        self.udp_config = {
            'key': os.urandom(16),
            'encryption': 'aes-128-ctr',
            'server': self.mqtt_server.public_endpoint,
            'port': self.mqtt_server.udp_port,
            'nonce': nonce,
            'local_sequence': 0,
            'remote_sequence': 0
        }
        if self.udp_handler:
            self.udp_handler.configure_encryption(self.udp_config)

        configured_audio_params = (
            getattr(self.mqtt_server, 'config', {})
            .get('xiaozhi', {})
            .get('audio_params', {})
        )
        hello_reply = {
            'type': 'hello',
            'version': version,
            'session_id': self.session_id,
            'transport': 'udp',
            'udp': {
                'server': self.udp_config['server'],
                'port': self.udp_config['port'],
                'encryption': self.udp_config['encryption'],
                'key': self.udp_config['key'].hex(),
                'nonce': nonce.hex()
            },
            'audio_params': configured_audio_params or audio_params or {}
        }

        return hello_reply

    def _generate_udp_header(
        self, length: int, timestamp: int, sequence: int,
        connection_id: int = None
    ) -> bytes:
        header = bytearray(16)
        header[0] = 1  # type
        header[2:4] = length.to_bytes(2, 'big')
        udp_connection_id = connection_id or self.connection_id
        header[4:8] = udp_connection_id.to_bytes(4, 'big')
        header[8:12] = timestamp.to_bytes(4, 'big')
        header[12:16] = sequence.to_bytes(4, 'big')
        return bytes(header)

    async def _handle_subscribe(self, subscribe_data: Dict[str, Any]):
        """处理SUBSCRIBE消息"""
        try:
            topic = subscribe_data['topic']
            packet_id = subscribe_data['packetId']

            logger.debug(f"客户端订阅主题: {topic}")

            # 发送订阅确认
            await self.protocol.send_suback(packet_id, 0)

        except Exception as e:
            logger.error(f"处理SUBSCRIBE消息失败: {e}")

    async def _handle_disconnect(self):
        """处理DISCONNECT消息"""
        logger.info(f"客户端主动断开连接: {self.client_id}")
        await self.close()

    async def _handle_close(self):
        """处理连接关闭"""
        logger.info(f"MQTT连接关闭: {self.client_id}")
        await self.close()

    async def _handle_error(self, error):
        """处理连接错误"""
        logger.error(f"MQTT连接错误: {self.client_id}, error: {error}")
        await self.close()

    async def _keep_alive_check(self):
        """心跳检查任务"""
        try:
            while self.is_connected_flag and not self._closed:
                await asyncio.sleep(self.keep_alive_interval / 1000 / 2)  # 检查间隔为心跳间隔的一半

                current_time = time.monotonic()
                if current_time - self.last_activity > self.keep_alive_interval / 1000 * 1.5:
                    logger.info(f"MQTT客户端心跳超时: {self.client_id}")
                    try:
                        await asyncio.wait_for(
                            self.notify_device_idle(),
                            timeout=self.goodbye_timeout,
                        )
                    except Exception as e:
                        logger.warning(
                            "MQTT心跳超时发送goodbye失败，继续关闭连接: {}", e
                        )
                    finally:
                        await self.close()
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳检查任务出错: {e}")

    def set_message_callback(self, callback: Callable[[str, str], None]):
        """设置消息接收回调"""
        self.message_callback = callback

    async def send_message(self, topic: str, payload: str):
        """发送MQTT消息"""
        if self._closed or not self.is_connected_flag:
            raise RuntimeError("MQTT connection is closed")

        try:
            await self.protocol.send_publish(topic, payload, qos=0)
            logger.debug(f"发送MQTT消息: topic={topic}, payload={payload}")

        except Exception as e:
            logger.error(f"发送MQTT消息失败: {e}")
            raise

    async def notify_device_idle(self, session_id: str = None) -> bool:
        """Send one session-scoped goodbye before the physical MQTT close."""
        async with self._goodbye_lock:
            target_session_id = session_id or self.session_id
            if (
                self._closed
                or not self.is_connected_flag
                or not self.udp_config
                or not self.reply_topic
                or not target_session_id
                or self._last_goodbye_session_id == target_session_id
            ):
                return False

            await self.send_message(
                self.reply_topic,
                json.dumps(
                    {"type": "goodbye", "session_id": target_session_id}
                ),
            )
            self._last_goodbye_session_id = target_session_id
            return True

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.is_connected_flag and not self._closed

    async def close(self):
        """关闭连接"""
        if not self._closed:
            self._closed = True
            self.is_connected_flag = False
            self.connect_processed_event.set()
            self.business_ready_event.set()
            if self._hello_business_ready_event is not None:
                self._hello_business_ready_event.set()
            # Run cleanup in a dedicated task. Shielding it lets a cancelled
            # first caller leave without falsely completing the close barrier;
            # later callers can still await the same cleanup owner.
            self._close_initiator = asyncio.current_task()
            self._close_task = asyncio.create_task(self._close_impl())

        close_task = self._close_task
        if close_task is None:
            return

        current_task = asyncio.current_task()
        dependency_tasks = {
            close_task,
            getattr(self.protocol, "_processing_task", None),
            getattr(self.protocol, "_dispatch_task", None),
        }
        if self.business_task is not self._close_initiator:
            dependency_tasks.add(self.business_task)
        if self.keep_alive_task is not self._close_initiator:
            dependency_tasks.add(self.keep_alive_task)
        # The dedicated closer can be waiting for these tasks. Let them unwind
        # instead of creating a reverse wait cycle.
        if current_task in dependency_tasks:
            return
        await asyncio.shield(close_task)

    async def _close_impl(self):
        """Own and complete physical cleanup independently of caller lifetime."""
        try:
            current_task = asyncio.current_task()

            # The socket/protocol task can time out while ConnectionService is
            # blocked in private config or component initialization. Cancel the
            # owning server task so its finally block releases the SessionContext
            # and any partially initialized runtime instead of leaking per retry.
            if (
                self.business_task
                and self.business_task is not current_task
                and self.business_task is not self._close_initiator
                and not self.business_task.done()
            ):
                self.business_task.cancel()
                # The business owner's finally block calls back into server
                # cleanup. Waiting for it here would create a close cycle:
                # close -> business finally -> transport.close -> close.
                # Give cancellation one loop turn, then let it unwind
                # independently while the physical socket is released.
                await asyncio.sleep(0)
                if not self.business_task.done():
                    tracker = getattr(
                        self.mqtt_server, "track_draining_task", None
                    )
                    if callable(tracker):
                        tracker(self.business_task, "MQTT业务任务")
                    else:
                        self.business_task.add_done_callback(
                            lambda task: self._consume_background_task(
                                task, "MQTT业务任务"
                            )
                        )

            # 取消心跳检查任务
            if (
                self.keep_alive_task
                and self.keep_alive_task is not current_task
                and self.keep_alive_task is not self._close_initiator
                and not self.keep_alive_task.done()
            ):
                self.keep_alive_task.cancel()
                await self._wait_cancelled_task(
                    self.keep_alive_task, "MQTT心跳任务"
                )

            if (
                self._startup_recovery_task
                and self._startup_recovery_task is not current_task
                and not self._startup_recovery_task.done()
            ):
                self._startup_recovery_task.cancel()
                await self._wait_cancelled_task(
                    self._startup_recovery_task, "MQTT会话恢复任务"
                )

            # 关闭协议处理器
            try:
                await asyncio.wait_for(
                    self.protocol.close(),
                    timeout=self.close_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("关闭MQTT协议处理器超时，强制中止socket")
                abort = getattr(self.protocol, "abort", None)
                if callable(abort):
                    abort()
            except (asyncio.CancelledError, Exception) as e:
                logger.error(f"关闭MQTT协议处理器失败: {e}")

            # Publish disconnect only after the physical protocol close barrier.
            try:
                await self.mqtt_server.on_client_disconnected(self)
            except (asyncio.CancelledError, Exception) as e:
                logger.error(f"通知服务器连接关闭失败: {e}")

            logger.info(f"MQTT连接已关闭: {self.client_id}")
        finally:
            self._close_complete.set()

    async def _wait_cancelled_task(self, task: asyncio.Task, label: str) -> None:
        done, _ = await asyncio.wait({task}, timeout=self.close_timeout)
        if task not in done:
            logger.warning(
                "{}取消后{}秒仍未退出，继续释放物理连接",
                label,
                self.close_timeout,
            )
            return
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"{label}退出失败: {exc}")

    @staticmethod
    def _consume_background_task(task: asyncio.Task, label: str) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"{label}退出失败: {exc}")
