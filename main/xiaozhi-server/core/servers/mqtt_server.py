import asyncio
import ipaddress
import json
import secrets
import socket
import time
import weakref
from typing import Dict, Any, Set
from config.logger import setup_logging
from core.protocols.mqtt_connection import MQTTConnection
from core.transport.mqtt_transport import MQTTTransport, UDPAudioHandler
from core.services.connection_service import ConnectionService
from core.services.native_mqtt_connection_registry import (
    NativeMqttConnectionRegistry,
)
from core.services.native_mqtt_call_manager import NativeMqttCallManager
from core.utils.mqtt_auth import normalize_signature_key, parse_mqtt_endpoint
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = setup_logging()


class MQTTServer:
    """
    原生MQTT服务器：直接处理MQTT协议连接
    集成到xiaozhi-server架构中
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()

        # 服务器配置
        server_config = config.get('mqtt_server', {})
        self.mqtt_port = server_config.get('port', 1883)
        self.udp_port = server_config.get('udp_port', self.mqtt_port)
        self.host = server_config.get('host', '0.0.0.0')
        self.public_endpoint = self._resolve_public_host(server_config)
        self.udp_bind_host = self.host
        self._udp_bind_host_config = server_config.get('udp_bind_host')
        self.signature_key = self._resolve_signature_key(config)
        if not self.signature_key:
            raise ValueError(
                "启用原生MQTT必须配置mqtt_server.signature_key或"
                "server.mqtt_signature_key"
            )
        self.message_queue_size = int(server_config.get('message_queue_size', 128))
        self.business_ready_timeout = float(
            server_config.get('business_ready_timeout', 30) or 30
        )
        self.close_timeout = max(
            0.1, float(server_config.get('close_timeout', 2) or 2)
        )
        self.shutdown_timeout = max(
            self.close_timeout,
            float(server_config.get('shutdown_timeout', 10) or 10),
        )
        self.goodbye_timeout = max(
            0.1, float(server_config.get('goodbye_timeout', 1) or 1)
        )
        self.max_connections = int(server_config.get('max_connections', 1000))
        self.max_pending_connections = int(
            server_config.get('max_pending_connections', 128)
        )
        self.max_payload_size = int(server_config.get('max_payload_size', 8192))

        # 连接管理
        self.connections: Dict[int, MQTTConnection] = {}
        self.client_id_map: Dict[str, int] = {}
        self.udp_handlers: Dict[int, UDPAudioHandler] = {}
        self.connection_id_counter = 0
        self._client_id_lock = asyncio.Lock()
        self._client_locks = weakref.WeakValueDictionary()
        self._client_reservations: Dict[str, int] = {}
        self._pending_connection_ids: Set[int] = set()
        self._cleanup_tasks: Dict[int, asyncio.Task] = {}
        self._draining_tasks: Set[asyncio.Task] = set()
        self._connection_handler_tasks: Set[asyncio.Task] = set()

        # 服务器实例
        self.mqtt_server = None
        self.udp_server = None

        # 连接服务
        self.connection_service = ConnectionService(config)
        self.connection_service.server = self

        # 活跃连接管理
        self.active_transports: Set[MQTTTransport] = set()
        self.connection_registry = NativeMqttConnectionRegistry()
        self.call_manager = NativeMqttCallManager(
            self.connection_registry,
            timeout_seconds=server_config.get("call_timeout", 60),
            silence_frame=self._create_silence_frame(),
        )

        # 心跳检查
        self.heartbeat_task = None
        self.heartbeat_interval = int(server_config.get('heartbeat_interval', 30))
        self._stop_event = asyncio.Event()
        self._started_event = asyncio.Event()
        self._is_running = False
        self._stopping = False
        self._shutdown_lock = asyncio.Lock()
        self._shutdown_task = None

    async def start(self):
        """启动MQTT服务器"""
        if self._is_running:
            logger.warning("MQTT服务器已经在运行中")
            return

        self._stop_event.clear()
        self._started_event.clear()
        self._stopping = False
        try:
            # 启动MQTT TCP服务器
            await self._start_mqtt_server()

            # 启动UDP服务器
            await self._start_udp_server()

            # 启动心跳检查
            self.heartbeat_task = asyncio.create_task(self._heartbeat_check())
            self._is_running = True
            self._started_event.set()

            logger.info(f"MQTT服务器启动成功: {self.host}:{self.mqtt_port}")
            logger.info(f"UDP服务器启动成功: {self.udp_bind_host}:{self.udp_port}")

            # 与 WebSocket 服务器保持一致，由上层持有该长期任务。
            await self._stop_event.wait()

        except Exception as e:
            logger.error(f"启动MQTT服务器失败: {e}")
            await self._await_shutdown_owner()
            raise
        finally:
            self._is_running = False
            self._started_event.clear()

    async def _start_mqtt_server(self):
        """启动MQTT TCP服务器"""
        self.mqtt_server = await asyncio.start_server(
            self._accept_mqtt_connection,
            self.host,
            self.mqtt_port
        )
        if self.mqtt_port == 0 and self.mqtt_server.sockets:
            self.mqtt_port = self.mqtt_server.sockets[0].getsockname()[1]

    async def _start_udp_server(self):
        """启动UDP服务器"""
        loop = asyncio.get_event_loop()

        sock = None
        bind_candidates = self._udp_bind_candidates()
        for index, bind_host in enumerate(bind_candidates):
            candidate = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                candidate.bind((bind_host, self.udp_port))
            except OSError as error:
                candidate.close()
                if index + 1 >= len(bind_candidates):
                    raise
                logger.warning(
                    "UDP无法绑定到对外地址 {}，回退监听 {}: {}",
                    bind_host,
                    bind_candidates[index + 1],
                    error,
                )
                continue
            sock = candidate
            self.udp_bind_host = bind_host
            break

        if sock is None:
            raise RuntimeError("UDP socket bind failed")
        sock.setblocking(False)

        # 创建UDP协议处理器
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPProtocol(self),
            sock=sock
        )

        self.udp_server = (transport, protocol)
        if self.udp_port == 0:
            self.udp_port = transport.get_extra_info("sockname")[1]

    def _udp_bind_candidates(self):
        """Prefer a local advertised IPv4 address so UDP replies keep that source IP."""
        explicit_bind_host = str(self._udp_bind_host_config or "").strip()
        if explicit_bind_host:
            return [explicit_bind_host]

        wildcard_hosts = {"", "0.0.0.0"}
        if self.host not in wildcard_hosts:
            return [self.host]

        try:
            public_ip = ipaddress.ip_address(self.public_endpoint)
        except ValueError:
            return [self.host]

        if public_ip.version == 4 and not public_ip.is_unspecified:
            return [self.public_endpoint, self.host]
        return [self.host]

    def _accept_mqtt_connection(self, reader, writer) -> None:
        """Track every accepted callback before its coroutine can yield."""
        task = asyncio.create_task(
            self._handle_mqtt_connection(reader, writer),
            name="mqtt-connection-handler",
        )
        self._connection_handler_tasks.add(task)

        def consume(completed_task):
            self._connection_handler_tasks.discard(completed_task)
            MQTTConnection._consume_background_task(
                completed_task, "MQTT连接处理任务"
            )

        task.add_done_callback(consume)

    async def _handle_mqtt_connection(self, reader, writer):
        """处理新的MQTT连接"""
        if self._stopping:
            await self._close_stream_writer(writer, "MQTT停服期间连接")
            return

        if (
            self.max_pending_connections > 0
            and len(self._pending_connection_ids) >= self.max_pending_connections
        ):
            logger.warning(
                "MQTT待认证连接数达到上限: {}", self.max_pending_connections
            )
            await self._close_stream_writer(writer, "MQTT待认证连接")
            return

        connection_id = self._generate_connection_id()

        try:
            # 获取客户端地址
            client_addr = writer.get_extra_info('peername')
            logger.info(f"新MQTT连接: {client_addr}, connection_id: {connection_id}")

            # 创建UDP音频处理器
            udp_handler = UDPAudioHandler(
                connection_id,
                self,
                {},  # 加密配置将在hello消息中设置
                allowed_remote_ip=client_addr[0] if client_addr else None,
            )

            # 创建MQTT连接处理器
            mqtt_connection = MQTTConnection(
                writer.get_extra_info('socket'),
                connection_id,
                self,
                udp_handler,
                reader=reader,
                writer=writer
            )
            mqtt_connection.business_task = asyncio.current_task()
            udp_handler.set_audio_interceptor(
                lambda payload, timestamp: self.call_manager.route_audio(
                    mqtt_connection.device_id, payload, timestamp
                )
            )

            # 创建MQTT传输层
            transport = MQTTTransport(mqtt_connection, udp_handler)

            # 注册连接
            self.connections[connection_id] = mqtt_connection
            self.active_transports.add(transport)
            self._pending_connection_ids.add(connection_id)

            try:
                await asyncio.wait_for(
                    mqtt_connection.connect_processed_event.wait(), timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning(f"MQTT CONNECT超时: connection_id={connection_id}")
                return
            finally:
                self._pending_connection_ids.discard(connection_id)

            if not mqtt_connection.connect_accepted:
                return

            # 提取连接头信息
            headers = {
                'x-real-ip': client_addr[0] if client_addr else 'unknown',
                'connection-type': 'mqtt'
            }

            try:
                # 使用ConnectionService处理连接
                await self.connection_service.handle_connection(transport, headers)

            except Exception as e:
                logger.error(f"ConnectionService处理MQTT连接失败: {e}")

        except Exception as e:
            logger.error(f"处理MQTT连接失败: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(connection_id)

    async def _cleanup_connection(self, connection_id: int):
        """Await the single cleanup owner without coupling it to caller cancellation."""
        if (
            connection_id not in self._cleanup_tasks
            and not self._connection_has_resources(connection_id)
        ):
            return
        cleanup_task = self._ensure_cleanup_task(connection_id)

        if cleanup_task is asyncio.current_task():
            return
        await asyncio.shield(cleanup_task)

    def _ensure_cleanup_task(self, connection_id: int) -> asyncio.Task:
        cleanup_task = self._cleanup_tasks.get(connection_id)
        if cleanup_task is None:
            cleanup_task = asyncio.create_task(
                self._cleanup_connection_impl(connection_id),
                name=f"mqtt-cleanup-{connection_id}",
            )
            self._cleanup_tasks[connection_id] = cleanup_task
        return cleanup_task

    def _connection_has_resources(self, connection_id: int) -> bool:
        if connection_id in self._pending_connection_ids:
            return True
        if connection_id in self.connections:
            return True
        if connection_id in self.client_id_map.values():
            return True
        if connection_id in self._client_reservations.values():
            return True
        return any(
            getattr(
                getattr(transport, "_mqtt_connection", None),
                "connection_id",
                None,
            )
            == connection_id
            for transport in self.active_transports
        )

    async def _cleanup_connection_impl(self, connection_id: int):
        """Physically release one connection before removing its registry entries."""
        connection = self.connections.get(connection_id)
        transports_to_remove = [
            transport
            for transport in list(self.active_transports)
            if (
                hasattr(transport, '_mqtt_connection')
                and transport._mqtt_connection.connection_id == connection_id
            )
        ]
        try:
            self._pending_connection_ids.discard(connection_id)
            if connection is not None:
                if (
                    connection.udp_config
                    and connection.is_connected()
                    and connection.reply_topic
                ):
                    try:
                        await asyncio.wait_for(
                            connection.notify_device_idle(),
                            timeout=self.goodbye_timeout,
                        )
                    except asyncio.TimeoutError:
                        logger.warning("MQTT连接关闭前发送goodbye超时")
                    except Exception as e:
                        logger.warning("MQTT连接关闭前发送goodbye失败: {}", e)
                try:
                    await asyncio.wait_for(
                        connection.close(), timeout=self.close_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "MQTT连接关闭超时，强制中止socket: {}", connection_id
                    )
                    abort = getattr(connection.protocol, "abort", None)
                    if callable(abort):
                        abort()
                    close_task = getattr(connection, "_close_task", None)
                    if close_task is not None and not close_task.done():
                        self.track_draining_task(
                            close_task,
                            f"MQTT连接关闭任务({connection_id})",
                        )

            # UDP 使用每个 Hello 独立的随机 cookie，清理该物理连接的全部别名。
            udp_handler = connection.udp_handler if connection is not None else None
            if udp_handler is not None:
                for session_id, registered in list(self.udp_handlers.items()):
                    if registered is udp_handler:
                        self.udp_handlers.pop(session_id, None)
                try:
                    await asyncio.wait_for(
                        udp_handler.close(), timeout=self.close_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "MQTT UDP处理器关闭超时: {}", connection_id
                    )

            for transport in transports_to_remove:
                try:
                    await asyncio.wait_for(
                        transport.close(), timeout=self.close_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("MQTT transport关闭超时: {}", connection_id)
                    abort = getattr(
                        getattr(transport, "_mqtt_connection", None),
                        "protocol",
                        None,
                    )
                    abort = getattr(abort, "abort", None)
                    if callable(abort):
                        abort()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"清理MQTT连接失败: {e}")
        finally:
            # A cleanup owner may be cancelled during process shutdown. Always
            # force the physical socket closed before publishing registry removal.
            if connection is not None:
                abort = getattr(connection.protocol, "abort", None)
                if callable(abort):
                    abort()
                close_task = getattr(connection, "_close_task", None)
                if close_task is not None and not close_task.done():
                    self.track_draining_task(
                        close_task,
                        f"MQTT连接关闭任务({connection_id})",
                    )

            for transport in transports_to_remove:
                self.active_transports.discard(transport)

            async with self._client_id_lock:
                for client_id, mapped_id in list(self.client_id_map.items()):
                    if mapped_id == connection_id:
                        self.client_id_map.pop(client_id, None)
                for client_id, reserved_id in list(
                    self._client_reservations.items()
                ):
                    if reserved_id == connection_id:
                        self._client_reservations.pop(client_id, None)
                self.connections.pop(connection_id, None)

            current_task = asyncio.current_task()
            if self._cleanup_tasks.get(connection_id) is current_task:
                self._cleanup_tasks.pop(connection_id, None)
            logger.info(f"MQTT连接清理完成: {connection_id}")

    async def _close_stream_writer(self, writer, label: str) -> None:
        """Bound close for sockets rejected before MQTTConnection exists."""
        writer.close()
        try:
            await asyncio.wait_for(
                writer.wait_closed(), timeout=self.close_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("{}关闭超时，强制中止transport", label)
            transport = getattr(writer, "transport", None)
            if transport is not None:
                transport.abort()
        except Exception:
            pass

    def track_draining_task(self, task: asyncio.Task, label: str) -> None:
        """Keep cancellation-resistant work visible until it actually exits."""
        if task is None or task.done():
            if task is not None:
                MQTTConnection._consume_background_task(task, label)
            return
        if task in self._draining_tasks:
            return
        self._draining_tasks.add(task)

        def consume(completed_task):
            self._draining_tasks.discard(completed_task)
            MQTTConnection._consume_background_task(completed_task, label)

        task.add_done_callback(consume)

    def _generate_connection_id(self) -> int:
        """生成连接ID"""
        self.connection_id_counter += 1
        return self.connection_id_counter

    async def _get_client_lock(self, client_id: str) -> asyncio.Lock:
        async with self._client_id_lock:
            lock = self._client_locks.get(client_id)
            if lock is None:
                lock = asyncio.Lock()
                self._client_locks[client_id] = lock
            return lock

    async def on_client_connected(
        self, mqtt_connection: MQTTConnection, accept_callback
    ) -> bool:
        """Atomically replace one clientId before acknowledging the new owner."""
        client_id = mqtt_connection.client_id
        if not client_id or self._stopping:
            return False

        client_lock = await self._get_client_lock(client_id)
        async with client_lock:
            if mqtt_connection._closed or self._stopping:
                return False

            reservation_active = False
            async with self._client_id_lock:
                old_id = self.client_id_map.get(client_id)
                identity_count = len(
                    set(self.client_id_map) | set(self._client_reservations)
                )
                if (
                    old_id is None
                    and client_id not in self._client_reservations
                    and self.max_connections > 0
                    and identity_count >= self.max_connections
                ):
                    logger.warning(
                        "MQTT活跃客户端数达到上限，拒绝clientId: {}", client_id
                    )
                    return False
                self._client_reservations[client_id] = (
                    mqtt_connection.connection_id
                )
                reservation_active = True
            try:
                if old_id and old_id != mqtt_connection.connection_id:
                    logger.info(f"检测到重复clientId，关闭旧连接: {client_id}")
                    cleanup_task = self._ensure_cleanup_task(old_id)
                    try:
                        await asyncio.shield(cleanup_task)
                    except asyncio.CancelledError as cancelled:
                        # Keep the per-client lock and capacity reservation until
                        # the predecessor's physical close barrier has completed.
                        try:
                            await asyncio.shield(cleanup_task)
                        except Exception as cleanup_error:
                            logger.error(
                                "取消接管时等待旧连接清理失败: {}", cleanup_error
                            )
                        raise cancelled

                if mqtt_connection._closed or self._stopping:
                    return False

                async with self._client_id_lock:
                    if (
                        self._client_reservations.get(client_id)
                        != mqtt_connection.connection_id
                    ):
                        return False
                    self.client_id_map[client_id] = mqtt_connection.connection_id
                    self._client_reservations.pop(client_id, None)
                    reservation_active = False

                await accept_callback()
            except BaseException:
                async with self._client_id_lock:
                    if (
                        self.client_id_map.get(client_id)
                        == mqtt_connection.connection_id
                    ):
                        self.client_id_map.pop(client_id, None)
                raise
            finally:
                if reservation_active:
                    async with self._client_id_lock:
                        if (
                            self._client_reservations.get(client_id)
                            == mqtt_connection.connection_id
                        ):
                            self._client_reservations.pop(client_id, None)

            logger.info(f"MQTT客户端已连接: {client_id}")
            return True

    async def on_client_disconnected(self, mqtt_connection: MQTTConnection):
        """客户端断开连接回调"""
        logger.info(f"MQTT客户端已断开: {mqtt_connection.client_id}")
        # Registry removal belongs to the physical cleanup owner. Scheduling
        # rather than awaiting avoids a close -> disconnect -> cleanup cycle.
        connection_id = mqtt_connection.connection_id
        if (
            connection_id in self.connections
            and connection_id not in self._cleanup_tasks
        ):
            self._ensure_cleanup_task(connection_id)

    async def register_connection_context(self, context, transport) -> bool:
        existing = self.connection_registry.resolve_device_now(
            getattr(context, "device_id", None)
        )
        registered = await self.connection_registry.register(
            context, transport
        )
        if (
            registered
            and existing is not None
            and existing.transport is not transport
        ):
            await self.call_manager.end_call(
                context.device_id,
                "设备连接被接管",
                notify_device=False,
                notify_peer=True,
                expected_session_id=getattr(
                    existing.transport, "session_id", None
                ),
            )
            try:
                await existing.transport.close()
            except Exception as error:
                logger.warning(
                    "关闭被接管的MQTT连接失败: device_id={}, error={}",
                    context.device_id,
                    error,
                )
        return registered

    async def unregister_connection_context(self, context, transport) -> bool:
        removed = await self.connection_registry.unregister(context, transport)
        if removed:
            await self.call_manager.end_call(
                context.device_id,
                "设备连接已断开",
                notify_device=False,
                notify_peer=True,
                expected_session_id=getattr(transport, "session_id", None),
            )
        return removed

    async def resolve_connection_context(self, client_id: str):
        return await self.connection_registry.resolve(client_id)

    async def get_connection_status(self, client_ids):
        return await self.connection_registry.status(client_ids)

    async def request_device_call(
        self, caller_mac: str, target_mac: str, caller_nickname: str = ""
    ):
        return await self.call_manager.request_call(
            caller_mac, target_mac, caller_nickname
        )

    async def accept_device_call(self, device_id: str):
        return await self.call_manager.accept_call(device_id)

    async def end_native_mqtt_call(
        self,
        device_id: str,
        reason: str = "",
        notify_device: bool = False,
        expected_session_id: str = None,
        expected_generation: int = None,
    ) -> bool:
        return await self.call_manager.end_call(
            device_id,
            reason,
            notify_device=notify_device,
            notify_peer=True,
            expected_session_id=expected_session_id,
            expected_generation=expected_generation,
        )

    async def handle_logical_hello(self, mqtt_connection) -> None:
        await self.call_manager.handle_logical_hello(
            mqtt_connection.device_id,
            mqtt_connection.session_id,
        )

    def bind_udp_session(
        self, mqtt_connection: MQTTConnection, udp_handler: UDPAudioHandler
    ) -> int:
        """Bind one unpredictable UDP cookie to the current Hello session."""
        for session_id, registered in list(self.udp_handlers.items()):
            if registered is udp_handler:
                self.udp_handlers.pop(session_id, None)

        while True:
            session_id = secrets.randbits(32)
            if session_id and session_id not in self.udp_handlers:
                break
        udp_handler.connection_id = session_id
        self.udp_handlers[session_id] = udp_handler
        return session_id

    async def send_udp_message(self, data: bytes, remote_addr: tuple):
        """发送UDP消息"""
        if not self.udp_server:
            raise RuntimeError("UDP server is not running")
        transport, protocol = self.udp_server
        transport.sendto(data, remote_addr)

    async def send_encrypted_audio(self, connection_id: int, audio_data: bytes,
                                   timestamp: int, sequence: int, remote_addr: tuple,
                                   encryption_config: Dict[str, Any]):
        """发送加密音频数据"""
        self.send_encrypted_audio_nowait(
            connection_id,
            audio_data,
            timestamp,
            sequence,
            remote_addr,
            encryption_config,
        )

    def send_encrypted_audio_nowait(
        self,
        connection_id: int,
        audio_data: bytes,
        timestamp: int,
        sequence: int,
        remote_addr: tuple,
        encryption_config: Dict[str, Any],
    ):
        header = self._generate_udp_header(connection_id, len(audio_data), timestamp, sequence)
        key = encryption_config.get('key') if encryption_config else None
        if key:
            cipher = Cipher(algorithms.AES(key), modes.CTR(header), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(audio_data) + encryptor.finalize()
            message = header + encrypted
        else:
            message = header + audio_data

        if not self.udp_server:
            raise RuntimeError("UDP server is not running")
        transport, _ = self.udp_server
        transport.sendto(message, remote_addr)

    def _generate_udp_header(self, connection_id: int, length: int, timestamp: int, sequence: int) -> bytes:
        """生成UDP消息头"""
        header = bytearray(16)
        header[0] = 1  # type
        header[2:4] = length.to_bytes(2, 'big')  # payload length
        header[4:8] = connection_id.to_bytes(4, 'big')  # connection id
        header[8:12] = timestamp.to_bytes(4, 'big')  # timestamp
        header[12:16] = sequence.to_bytes(4, 'big')  # sequence
        return bytes(header)

    async def _heartbeat_check(self):
        """心跳检查任务"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                # 检查所有连接的状态
                dead_connections = []
                for connection_id, connection in self.connections.items():
                    if not connection.is_connected():
                        dead_connections.append(connection_id)

                # 清理死连接
                for connection_id in dead_connections:
                    logger.info(f"清理死连接: {connection_id}")
                    await self._cleanup_connection(connection_id)

                await self.call_manager.cleanup_timeouts()

                # 记录活跃连接数
                active_count = len(self.connections)
                if active_count > 0:
                    logger.info(f"MQTT活跃连接数: {active_count}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳检查任务出错: {e}")

    async def stop(self):
        """停止MQTT服务器"""
        async with self._shutdown_lock:
            self._prune_finished_lifecycle_tasks()
            shutdown_in_progress = (
                self._shutdown_task is not None
                and not self._shutdown_task.done()
            )
            if (
                not self._is_running
                and self._shutdown_resources_released()
                and not shutdown_in_progress
            ):
                self._stop_event.set()
                return True

            logger.info("正在停止MQTT服务器...")
            shutdown_task = self._ensure_shutdown_owner()

        shutdown_result = await asyncio.shield(shutdown_task)
        # Existing lifecycle test doubles and older protocol servers return
        # None on success. Only an explicit False means cleanup is partial.
        complete = shutdown_result is not False
        if complete:
            logger.info("MQTT服务器已停止")
        else:
            status = self.get_server_status()
            logger.error(
                "MQTT监听器已停止，但仍有未退出任务: handlers={}, draining={}",
                status["connection_handler_tasks"],
                status["draining_tasks"],
            )
        return complete

    def _ensure_shutdown_owner(self) -> asyncio.Task:
        """Create or reuse the single physical shutdown owner."""
        if self._shutdown_task is None or self._shutdown_task.done():
            self._shutdown_task = asyncio.create_task(
                self._run_shutdown_owner()
            )
        return self._shutdown_task

    async def _await_shutdown_owner(self):
        """Wait for shutdown without letting caller cancellation kill it."""
        return await asyncio.shield(self._ensure_shutdown_owner())

    async def _run_shutdown_owner(self):
        try:
            return await self._shutdown_resources()
        finally:
            # A cancelled stop waiter must not leave start() blocked forever.
            self._stop_event.set()
            self._is_running = False
            self._started_event.clear()

    def _prune_finished_lifecycle_tasks(self) -> None:
        for connection_id, task in list(self._cleanup_tasks.items()):
            if task.done() and self._cleanup_tasks.get(connection_id) is task:
                self._cleanup_tasks.pop(connection_id, None)
        for task in list(self._connection_handler_tasks):
            if task.done():
                self._connection_handler_tasks.discard(task)
        for task in list(self._draining_tasks):
            if task.done():
                self._draining_tasks.discard(task)

    def _shutdown_resources_released(self) -> bool:
        """Return true only when every MQTT-owned resource is gone."""
        heartbeat_alive = (
            self.heartbeat_task is not None
            and not self.heartbeat_task.done()
        )
        return not (
            self.mqtt_server
            or self.udp_server
            or heartbeat_alive
            or self.connections
            or self.client_id_map
            or self.udp_handlers
            or self.active_transports
            or self._client_reservations
            or self._pending_connection_ids
            or self._cleanup_tasks
            or self.connection_registry.count
            or self.call_manager.count
            or self.call_manager.background_task_count
            or any(
                not task.done()
                for task in self._connection_handler_tasks
            )
            or any(not task.done() for task in self._draining_tasks)
        )

    async def _shutdown_resources(self):
        """幂等释放 MQTT/UDP 监听器、连接和后台任务。"""
        self._stopping = True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.shutdown_timeout

        # Stop accepting before taking any connection/task snapshot.
        if self.mqtt_server:
            self.mqtt_server.close()
            await self.mqtt_server.wait_closed()
            self.mqtt_server = None
        # Let callbacks already queued by the event loop enter the synchronous
        # tracking wrapper before handler/connection snapshots are taken.
        await asyncio.sleep(0)

        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            await asyncio.gather(self.heartbeat_task, return_exceptions=True)
        self.heartbeat_task = None

        # Start every cleanup owner first, then wait against one global deadline.
        connection_ids = (
            set(self.connections)
            | set(self._cleanup_tasks)
            | set(self.client_id_map.values())
            | set(self._client_reservations.values())
            | set(self._pending_connection_ids)
        )
        connection_ids.update(
            connection_id
            for connection_id in (
                getattr(
                    getattr(transport, "_mqtt_connection", None),
                    "connection_id",
                    None,
                )
                for transport in self.active_transports
            )
            if connection_id is not None
        )
        cleanup_tasks = [
            self._ensure_cleanup_task(connection_id)
            for connection_id in connection_ids
            if self._connection_has_resources(connection_id)
            or connection_id in self._cleanup_tasks
        ]
        pending_cleanup = await self._wait_until_deadline(
            cleanup_tasks, deadline
        )
        if pending_cleanup:
            logger.warning(
                "MQTT停服清理超过全局时限，强制取消{}个清理任务",
                len(pending_cleanup),
            )
            for task in pending_cleanup:
                task.cancel()
            await asyncio.gather(*pending_cleanup, return_exceptions=True)

        # Accepted callbacks are tracked synchronously by _accept_mqtt_connection.
        handler_tasks = [
            task
            for task in self._connection_handler_tasks
            if not task.done()
        ]
        for task in handler_tasks:
            task.cancel()
        pending_handlers = await self._wait_until_deadline(
            handler_tasks, deadline
        )
        for task in pending_handlers:
            self.track_draining_task(task, "MQTT连接处理任务")

        draining_tasks = [
            task for task in self._draining_tasks if not task.done()
        ]
        for task in draining_tasks:
            task.cancel()
        pending_draining = await self._wait_until_deadline(
            draining_tasks, deadline
        )
        if pending_draining:
            logger.warning(
                "MQTT停服后仍有{}个取消不响应任务", len(pending_draining)
            )

        # Defensive closure for any transport whose connection registration was
        # corrupted by an earlier failure.
        transport_tasks = [
            asyncio.create_task(self._close_transport(transport))
            for transport in list(self.active_transports)
        ]
        pending_transports = await self._wait_until_deadline(
            transport_tasks, deadline
        )
        for task in pending_transports:
            task.cancel()
        if pending_transports:
            await asyncio.gather(
                *pending_transports, return_exceptions=True
            )

        # Close any orphaned UDP session left behind by a corrupted registry.
        for udp_handler in set(self.udp_handlers.values()):
            await udp_handler.close()
        self.udp_handlers.clear()

        # 关闭UDP服务器
        if self.udp_server:
            transport, protocol = self.udp_server
            transport.close()
            self.udp_server = None

        await self.call_manager.clear()
        await self.connection_registry.clear()
        self._prune_finished_lifecycle_tasks()
        return self._shutdown_resources_released()

    @staticmethod
    def _create_silence_frame():
        try:
            import opuslib_next

            encoder = opuslib_next.Encoder(
                16000, 1, opuslib_next.APPLICATION_AUDIO
            )
            return encoder.encode(bytes(960 * 2), 960)
        except Exception as error:
            logger.warning("Native MQTT通话静音帧初始化失败: {}", error)
            return None

    async def _wait_until_deadline(self, tasks, deadline):
        pending = {task for task in tasks if task is not None and not task.done()}
        if not pending:
            return set()
        remaining = max(0.0, deadline - asyncio.get_running_loop().time())
        _, pending = await asyncio.wait(pending, timeout=remaining)
        return pending

    async def _close_transport(self, transport) -> None:
        try:
            await asyncio.wait_for(
                transport.close(), timeout=self.close_timeout
            )
        except asyncio.TimeoutError:
            connection = getattr(transport, "_mqtt_connection", None)
            abort = getattr(
                getattr(connection, "protocol", None), "abort", None
            )
            if callable(abort):
                abort()
        finally:
            self.active_transports.discard(transport)

    async def update_config(self, new_config: Dict[str, Any]) -> bool:
        """更新非监听配置；监听地址变化由 MultiProtocolServer 重建实例。"""
        try:
            self.config = new_config
            server_config = new_config.get('mqtt_server', {})
            self.public_endpoint = self._resolve_public_host(server_config)
            self._udp_bind_host_config = server_config.get('udp_bind_host')
            signature_key = self._resolve_signature_key(new_config)
            if not signature_key:
                raise ValueError(
                    "启用原生MQTT必须配置mqtt_server.signature_key或"
                    "server.mqtt_signature_key"
                )
            self.signature_key = signature_key
            self.message_queue_size = int(server_config.get('message_queue_size', 128))
            self.business_ready_timeout = float(
                server_config.get('business_ready_timeout', 30) or 30
            )
            self.close_timeout = max(
                0.1, float(server_config.get('close_timeout', 2) or 2)
            )
            self.shutdown_timeout = max(
                self.close_timeout,
                float(server_config.get('shutdown_timeout', 10) or 10),
            )
            self.goodbye_timeout = max(
                0.1, float(server_config.get('goodbye_timeout', 1) or 1)
            )
            self.max_connections = int(server_config.get('max_connections', 1000))
            self.max_pending_connections = int(
                server_config.get('max_pending_connections', 128)
            )
            self.max_payload_size = int(server_config.get('max_payload_size', 8192))
            self.heartbeat_interval = int(server_config.get('heartbeat_interval', 30))

            # 已建立连接保留会话快照，新连接使用新配置。
            self.connection_service = ConnectionService(new_config)
            self.connection_service.server = getattr(self, "management_owner", self)
            return True
        except Exception as e:
            logger.error(f"更新MQTT服务器配置失败: {e}")
            return False

    @staticmethod
    def _resolve_signature_key(config: Dict[str, Any]) -> str:
        server_config = config.get('mqtt_server', {})
        return (
            normalize_signature_key(server_config.get('signature_key'))
            or normalize_signature_key(
                config.get('server', {}).get('mqtt_signature_key')
            )
        )

    @staticmethod
    def _resolve_public_host(server_config: Dict[str, Any]) -> str:
        host, _ = parse_mqtt_endpoint(
            server_config.get('public_endpoint'),
            None,
        )
        return host or 'localhost'

    async def apply_config(self, new_config: Dict[str, Any]) -> bool:
        return await self.update_config(new_config)

    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'type': 'mqtt',
            'host': self.host,
            'mqtt_port': self.mqtt_port,
            'udp_port': self.udp_port,
            'active_connections': len(self.connections),
            'active_transports': len(self.active_transports),
            'pending_connections': len(self._pending_connection_ids),
            'cleanup_tasks': len(self._cleanup_tasks),
            'draining_tasks': sum(
                not task.done() for task in self._draining_tasks
            ),
            'connection_handler_tasks': sum(
                not task.done()
                for task in self._connection_handler_tasks
            ),
            'stopping': self._stopping,
        }


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP协议处理器"""

    def __init__(self, mqtt_server: MQTTServer):
        self.mqtt_server = mqtt_server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        """接收UDP数据报"""
        try:
            # 解析UDP消息头
            if len(data) < 16:
                return

            packet_type = data[0]
            if packet_type != 1:
                return

            payload_length = int.from_bytes(data[2:4], 'big')
            if len(data) != 16 + payload_length:
                logger.warning(
                    "UDP数据报长度不匹配: actual={}, expected={}",
                    len(data),
                    16 + payload_length,
                )
                return

            connection_id = int.from_bytes(data[4:8], 'big')
            timestamp = int.from_bytes(data[8:12], 'big')
            sequence = int.from_bytes(data[12:16], 'big')
            header = data[:16]
            encrypted_payload = data[16:16 + payload_length]

            # 找到对应的UDP处理器
            udp_handler = self.mqtt_server.udp_handlers.get(connection_id)
            if udp_handler:
                udp_handler.on_udp_message(header, encrypted_payload, payload_length, timestamp, sequence, addr)

        except Exception as e:
            logger.error(f"处理UDP数据报失败: {e}")

    def error_received(self, exc):
        logger.error(f"UDP协议错误: {exc}")
