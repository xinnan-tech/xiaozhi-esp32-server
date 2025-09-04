import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update
import json

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict, redis=None, camera_handler=None):
        self.config = config
        self.logger = setup_logging()
        self.redis = redis
        self.camera_handler = camera_handler
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection, host, port, process_request=self._http_response
        ):
            # 启动摄像头控制订阅
            if self.redis is not None:
                asyncio.create_task(self._camera_cmd_sub())
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """处理新连接，每次创建独立的ConnectionHandler"""
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理连接时出错: {e}")
        finally:
            # 确保从活动连接集合中移除
            self.active_connections.discard(handler)
            # 强制关闭连接（如果还没有关闭的话）
            try:
                # 安全地检查WebSocket状态并关闭
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
                else:
                    # 如果没有closed属性，直接尝试关闭
                    await websocket.close()
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"服务器端强制关闭连接时出错: {close_error}"
                )

    async def _http_response(self, websocket, request_headers):
        # 检查是否为 WebSocket 升级请求
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # 如果是 WebSocket 请求，返回 None 允许握手继续
            return None
        else:
            # 如果是普通 HTTP 请求，返回 "server is running"
            return websocket.respond(200, "Server is running\n")

    async def _camera_cmd_sub(self):
        try:
            # 检查Redis连接状态
            if self.redis is None:
                self.logger.bind(tag=TAG).error("Redis连接为空，无法订阅摄像头命令")
                return
                
            # 测试Redis连接
            try:
                await self.redis.ping()
                self.logger.bind(tag=TAG).info("Redis连接正常")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Redis连接失败: {e}")
                return
                
            self.logger.bind(tag=TAG).info("开始订阅摄像头命令频道: camera:cmd:*")
            pubsub = self.redis.pubsub()
            await pubsub.psubscribe("camera:cmd:*")
            self.logger.bind(tag=TAG).info("成功订阅摄像头命令频道")

            async for msg in pubsub.listen():
                self.logger.bind(tag=TAG).info(f"收到Redis消息: {msg}")

                if msg.get("type") != "pmessage":
                    self.logger.bind(tag=TAG).info(f"跳过非模式消息: {msg.get('type')}")
                    continue

                channel = msg.get("channel", "")
                payload = msg.get("data", "")
                self.logger.bind(tag=TAG).info(f"处理摄像头命令 - 频道: {channel}, 数据: {payload}")

                # 提取 deviceId
                # 修复：正确处理包含冒号的设备ID
                # 频道格式：camera:cmd:80:b5:4e:c7:78:a4
                # 需要提取：80:b5:4e:c7:78:a4
                if channel.startswith("camera:cmd:"):
                    device_id = channel[11:]  # 去掉 "camera:cmd:" 前缀 (11个字符)
                    self.logger.bind(tag=TAG).info(f"原始频道: {channel}")
                    self.logger.bind(tag=TAG).info(f"前缀长度: 11, 提取结果: {device_id}")
                else:
                    device_id = channel
                self.logger.bind(tag=TAG).info(f"提取的设备ID: {device_id}")

                # 在活动连接中找到对应设备
                target = None
                active_connections_count = len(list(self.active_connections))
                self.logger.bind(tag=TAG).info(f"当前活跃连接数: {active_connections_count}")

                for conn in list(self.active_connections):
                    conn_device_id = getattr(conn, "device_id", None)
                    self.logger.bind(tag=TAG).info(f"检查连接: {conn}, device_id: {conn_device_id}")
                    if conn_device_id == device_id:
                        target = conn
                        self.logger.bind(tag=TAG).info(f"找到目标连接: {target}")
                        break

                if target is None:
                    self.logger.bind(tag=TAG).warning(f"未找到设备ID为 {device_id} 的活跃连接")
                    # 尝试重新建立连接
                    self.logger.bind(tag=TAG).info(f"尝试重新建立与设备 {device_id} 的连接...")
                    # 这里可以添加重连逻辑，暂时跳过
                    continue

                try:
                    data = json.loads(payload)
                    action = data.get("action")
                    self.logger.bind(tag=TAG).info(f"处理摄像头动作: {action}")

                    if action == "start":
                        args = {}
                        if "fps" in data: args["fps"] = data["fps"]
                        if "quality" in data: args["quality"] = data["quality"]
                        rpc = {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"self.camera.stream.start","arguments":args}}
                        self.logger.bind(tag=TAG).info(f"发送启动命令: {rpc}")
                        await target.websocket.send(json.dumps({"type":"mcp","payload":rpc}))
                        self.logger.bind(tag=TAG).info("启动命令发送成功")
                    elif action == "stop":
                        rpc = {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"self.camera.stream.stop"}}
                        self.logger.bind(tag=TAG).info(f"发送停止命令: {rpc}")
                        await target.websocket.send(json.dumps({"type":"mcp","payload":rpc}))
                        self.logger.bind(tag=TAG).info("停止命令发送成功")
                except Exception as e:
                    self.logger.bind(tag=TAG).exception(f"处理摄像头指令失败: {e}")
        except Exception as e:
            self.logger.bind(tag=TAG).exception(f"摄像头指令订阅失败: {e}")

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False
