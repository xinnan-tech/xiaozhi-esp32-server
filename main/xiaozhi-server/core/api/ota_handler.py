import json
import time
import base64
import os
import re
import glob
from typing import Dict, List, Tuple
from aiohttp import web

from core.auth import AuthManager
from core.utils.util import get_local_ip, get_vision_url
from core.utils.mqtt_auth import (
    generate_password_signature,
    normalize_signature_key,
    parse_mqtt_endpoint,
)
from core.api.base_handler import BaseHandler

TAG = __name__


def _safe_basename(filename: str) -> str:
    # Prevent directory traversal
    return os.path.basename(filename)


def _parse_version(ver: str) -> Tuple[int, ...]:
    # conservative parser: split by non-digit, keep numeric parts
    parts = re.findall(r"\d+", ver)
    return tuple(int(p) for p in parts) if parts else (0,)


def _is_higher_version(a: str, b: str) -> bool:
    """Return True if version string a > b (semver-like numeric compare)."""
    ta = _parse_version(a)
    tb = _parse_version(b)
    # compare tuple lexicographically, but allow different lengths
    maxlen = max(len(ta), len(tb))
    for i in range(maxlen):
        ai = ta[i] if i < len(ta) else 0
        bi = tb[i] if i < len(tb) else 0
        if ai > bi:
            return True
        if ai < bi:
            return False
    return False


class OTAHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        auth_config = config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # 设备白名单
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        secret_key = config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds")
        self.auth = AuthManager(secret_key=secret_key, expire_seconds=expire_seconds)

        # firmware storage
        self.bin_dir = os.path.join(os.getcwd(), "data", "bin")
        # cache structure: { 'updated_at': timestamp, 'ttl': seconds, 'files_by_model': { model: [(version, filename), ...] } }
        self._bin_cache: Dict = {
            "updated_at": 0,
            "ttl": config.get("firmware_cache_ttl", 30),
            "files_by_model": {},
        }

    def _refresh_bin_cache_if_needed(self):
        now = int(time.time())
        ttl = int(self._bin_cache.get("ttl", 30))
        if now - int(
            self._bin_cache.get("updated_at", 0)
        ) < ttl and self._bin_cache.get("files_by_model"):
            return

        files_by_model: Dict[str, List[Tuple[str, str]]] = {}
        try:
            if not os.path.isdir(self.bin_dir):
                os.makedirs(self.bin_dir, exist_ok=True)

            # match files like model_1.2.3.bin (allow dots, dashes, underscores in model and version)
            pattern = os.path.join(self.bin_dir, "*.bin")
            for path in glob.glob(pattern):
                fname = os.path.basename(path)
                # filename format: {model}_{version}.bin
                m = re.match(r"^(.+?)_([0-9][A-Za-z0-9\.\-_]*)\.bin$", fname)
                if not m:
                    # skip files not conforming to naming rule
                    continue
                model = m.group(1)
                version = m.group(2)
                files_by_model.setdefault(model, []).append((version, fname))

            # sort versions for each model descending
            for model, items in files_by_model.items():
                items.sort(key=lambda it: _parse_version(it[0]), reverse=True)

            self._bin_cache["files_by_model"] = files_by_model
            self._bin_cache["updated_at"] = now
            self.logger.bind(tag=TAG).info(
                f"Firmware cache refreshed: {len(files_by_model)} models"
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"刷新固件缓存失败: {e}")
            # keep previous cache if any

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket", "")

        if "你的" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def handle_post(self, request):
        """处理 OTA POST 请求

        This handler will:
        - read device id/client id (as before)
        - attempt to determine device model and current firmware version (prefer headers, fallback to body)
        - check data/bin for newer firmware for that model
        - if found a newer firmware, set firmware.url to the download endpoint
        """
        try:
            data = await request.text()
            self.logger.bind(tag=TAG).debug(f"OTA请求方法: {request.method}")
            self.logger.bind(tag=TAG).debug(f"OTA请求头: {request.headers}")
            self.logger.bind(tag=TAG).debug(f"OTA请求数据: {data}")

            device_id = request.headers.get("device-id", "")
            if device_id:
                self.logger.bind(tag=TAG).info(f"OTA请求设备ID: {device_id}")
            else:
                raise Exception("OTA请求设备ID为空")

            client_id = request.headers.get("client-id", "")
            if client_id:
                self.logger.bind(tag=TAG).info(f"OTA请求ClientID: {client_id}")
            else:
                raise Exception("OTA请求ClientID为空")

            data_json = {}
            try:
                data_json = json.loads(data) if data else {}
            except Exception:
                data_json = {}

            server_config = self.config["server"]
            # Distinguish ports:
            # - websocket_port is used to construct websocket URL (server["port"])
            # - http_port is used to construct OTA download URLs (server["http_port"])
            websocket_port = int(server_config.get("port", 8000))
            http_port = int(server_config.get("http_port", 8003))
            local_ip = get_local_ip()

            # Determine device model (prefer headers)
            device_model = ""
            # header candidates
            for h in ("device-model", "device_model", "model"):
                if h in request.headers:
                    device_model = request.headers.get(h, "").strip()
                    break
            # body fallback
            if not device_model:
                try:
                    if "board" in data_json and isinstance(data_json["board"], dict):
                        device_model = data_json["board"].get("type", "")
                    elif "model" in data_json:
                        device_model = data_json.get("model", "")
                except Exception:
                    device_model = ""
            if not device_model:
                device_model = "default"

            # Determine device current version (prefer headers)
            device_version = ""
            for h in (
                "device-version",
                "device_version",
                "firmware-version",
                "app-version",
                "application-version",
            ):
                if h in request.headers:
                    device_version = request.headers.get(h, "").strip()
                    break
            if not device_version:
                try:
                    device_version = data_json.get("application", {}).get("version", "")
                except Exception:
                    device_version = ""
            if not device_version:
                device_version = "0.0.0"

            return_json = {
                "server_time": {
                    "timestamp": int(round(time.time() * 1000)),
                    "timezone_offset": server_config.get("timezone_offset", 8) * 60,
                },
                "firmware": {
                    "version": device_version,
                    "url": "",
                },
            }

            # ========== 协议下发逻辑 ==========
            # 按照原版逻辑：总是下发 WebSocket，如果启用了 MQTT 则额外下发 MQTT 和 UDP
            # 这样设备有回退能力：如果 MQTT 连接失败，还可以使用 WebSocket

            mqtt_server_config = self.config.get("mqtt_server", {})
            enabled_protocols = self.config.get("enabled_protocols")
            if isinstance(enabled_protocols, list):
                mqtt_protocol_enabled = "mqtt" in enabled_protocols
            else:
                protocol_config = self.config.get("protocols", {})
                requested_protocols = protocol_config.get(
                    "enabled_protocols", []
                )
                mqtt_protocol_enabled = (
                    protocol_config.get("mqtt_enabled") is True
                    or "mqtt" in requested_protocols
                )
            mqtt_server_enabled = bool(
                mqtt_server_config.get("enabled") and mqtt_protocol_enabled
            )
            mqtt_gateway_endpoint = server_config.get("mqtt_gateway")
            if not mqtt_gateway_endpoint or str(mqtt_gateway_endpoint).lower() == "null":
                mqtt_gateway_endpoint = None

            # 生成通用的 MQTT 凭证信息
            def _build_mqtt_credentials():
                try:
                    group_id = f"GID_{device_model}".replace(":", "_").replace(" ", "_")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"获取设备型号失败: {e}")
                    group_id = "GID_default"

                mac_address_safe = device_id.replace(":", "_")
                mqtt_client_id = f"{group_id}@@@{mac_address_safe}@@@{mac_address_safe}"

                # 构建用户数据
                user_data = {"ip": local_ip}
                try:
                    user_data_json = json.dumps(user_data)
                    username = base64.b64encode(user_data_json.encode("utf-8")).decode("utf-8")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"生成用户名失败: {e}")
                    username = ""

                return group_id, mac_address_safe, mqtt_client_id, username

            # ========== 1. 总是下发 WebSocket 配置（作为基础/回退方案）==========
            ws_token = ""
            if self.auth_enable:
                if self.allowed_devices:
                    if device_id not in self.allowed_devices:
                        ws_token = self.auth.generate_token(client_id, device_id)
                else:
                    ws_token = self.auth.generate_token(client_id, device_id)

            return_json["websocket"] = {
                "url": self._get_websocket_url(local_ip, websocket_port),
                "token": ws_token,
            }

            # ========== 2. 如果启用了原生 MQTT 服务器，额外下发 MQTT 配置 ==========
            signature_key = normalize_signature_key(
                mqtt_server_config.get("signature_key")
                or server_config.get("mqtt_signature_key")
            )
            native_mqtt_ready = bool(mqtt_server_enabled and signature_key)
            if mqtt_server_enabled and not signature_key:
                self.logger.bind(tag=TAG).error(
                    "原生MQTT已启用但未配置签名密钥，跳过Native配置下发"
                )

            if native_mqtt_ready:
                try:
                    mqtt_host, mqtt_port = parse_mqtt_endpoint(
                        mqtt_server_config.get("public_endpoint"),
                        int(mqtt_server_config.get("port", 1883)),
                    )
                except (TypeError, ValueError) as exc:
                    self.logger.bind(tag=TAG).error(f"MQTT endpoint配置无效: {exc}")
                    mqtt_host, mqtt_port = "", None

                placeholder_keywords = ("localhost", "0.0.0.0", "your", "example")
                if not mqtt_host or any(
                    keyword in mqtt_host.lower() for keyword in placeholder_keywords
                ):
                    mqtt_host = local_ip
                    self.logger.bind(tag=TAG).info(
                        f"检测到 public_endpoint 为占位符，自动使用本地IP: {local_ip}"
                    )

                if mqtt_port is None:
                    native_mqtt_ready = False

            if native_mqtt_ready:

                group_id, mac_address_safe, mqtt_client_id, username = _build_mqtt_credentials()

                mqtt_password = generate_password_signature(
                    mqtt_client_id + "|" + username, signature_key
                )

                return_json["mqtt"] = {
                    "endpoint": f"{mqtt_host}:{mqtt_port}",
                    "client_id": mqtt_client_id,
                    "username": username,
                    "password": mqtt_password,
                    "publish_topic": "device-server",
                    "subscribe_topic": f"devices/p2p/{mac_address_safe}",
                }

                self.logger.bind(tag=TAG).info(
                    f"为设备 {device_id} 下发原生MQTT配置: {mqtt_host}:{mqtt_port}"
                )

            # ========== 3. 如果配置了外部 MQTT 网关，额外下发 MQTT 配置 ==========
            elif mqtt_gateway_endpoint:
                group_id, mac_address_safe, mqtt_client_id, username = _build_mqtt_credentials()

                # 生成密码
                mqtt_password = ""
                signature_key = server_config.get("mqtt_signature_key", "")
                if signature_key:
                    mqtt_password = generate_password_signature(
                        mqtt_client_id + "|" + username, signature_key
                    )
                    if not mqtt_password:
                        mqtt_password = ""
                else:
                    self.logger.bind(tag=TAG).warning("缺少MQTT签名密钥，密码留空")

                return_json["mqtt"] = {
                    "endpoint": mqtt_gateway_endpoint,
                    "client_id": mqtt_client_id,
                    "username": username,
                    "password": mqtt_password,
                    "publish_topic": "device-server",
                    "subscribe_topic": f"devices/p2p/{mac_address_safe}",
                }

                self.logger.bind(tag=TAG).info(f"为设备 {device_id} 下发MQTT网关配置: {mqtt_gateway_endpoint}")

            # 记录最终下发的协议
            protocols = ["websocket"]
            if "mqtt" in return_json:
                protocols.append("mqtt")
            self.logger.bind(tag=TAG).info(f"为设备 {device_id} 下发协议配置: {', '.join(protocols)}")

            # Now check firmware files for updates
            try:
                self._refresh_bin_cache_if_needed()
                files_by_model = self._bin_cache.get("files_by_model", {})
                candidates = files_by_model.get(device_model, [])

                self.logger.bind(tag=TAG).info(
                    f"查找型号 {device_model} 的固件，找到 {len(candidates)} 个候选"
                )

                chosen_url = ""
                chosen_version = device_version

                # candidates are sorted descending by version
                for ver, fname in candidates:
                    if _is_higher_version(ver, device_version):
                        # build download url (only allow download via our download endpoint)
                        chosen_version = ver
                        # Use get_vision_url to get the base URL and replace the path
                        vision_url = get_vision_url(self.config)
                        # Replace the path from "/mcp/vision/explain" to "/xiaozhi/ota/download/{fname}"
                        chosen_url = vision_url.replace(
                            "/mcp/vision/explain", f"/xiaozhi/ota/download/{fname}"
                        )
                        break

                if chosen_url:
                    return_json["firmware"]["version"] = chosen_version
                    return_json["firmware"]["url"] = chosen_url
                    self.logger.bind(tag=TAG).info(
                        f"为设备 {device_id} 下发固件 {chosen_version} [如果地址前缀有误，请检查配置文件中的server.vision_explain]-> {chosen_url} "
                    )
                else:
                    self.logger.bind(tag=TAG).info(
                        f"设备 {device_id} 固件已是最新: {device_version}"
                    )

            except Exception as e:
                self.logger.bind(tag=TAG).error(f"检查固件版本时出错: {e}")

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA POST处理异常: {e}")
            return_json = {"success": False, "message": "request error."}
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """处理 OTA GET 请求"""
        try:
            server_config = self.config["server"]
            local_ip = get_local_ip()
            # use websocket port for websocket URL
            websocket_port = int(server_config.get("port", 8000))
            websocket_url = self._get_websocket_url(local_ip, websocket_port)
            message = f"OTA接口运行正常，向设备发送的websocket地址是：{websocket_url}"
            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA GET请求异常: {e}")
            response = web.Response(text="OTA接口异常", content_type="text/plain")
        finally:
            self._add_cors_headers(response)
            return response

    async def handle_download(self, request):
        """
        下载固件接口
        URL: /xiaozhi/ota/download/{filename}
        - 只允许下载 data/bin 目录下的 .bin 文件
        - filename 必须是 basename 且匹配安全的模式
        """
        try:
            fname = request.match_info.get("filename", "")
            if not fname:
                raise web.HTTPBadRequest(text="filename required")

            # sanitize
            fname = _safe_basename(fname)
            # pattern: allow letters, numbers, dot, underscore, dash
            if not re.match(r"^[A-Za-z0-9\.\-_]+\.bin$", fname):
                raise web.HTTPBadRequest(text="invalid filename")

            file_path = os.path.join(self.bin_dir, fname)
            # ensure realpath is under bin_dir
            file_real = os.path.realpath(file_path)
            bin_dir_real = os.path.realpath(self.bin_dir)
            if (
                not file_real.startswith(bin_dir_real + os.sep)
                and file_real != bin_dir_real
            ):
                raise web.HTTPForbidden(text="forbidden")

            if not os.path.isfile(file_real):
                raise web.HTTPNotFound(text="file not found")

            # use FileResponse to stream file
            resp = web.FileResponse(path=file_real)
        except web.HTTPError as e:
            resp = e
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"固件下载异常: {e}")
            resp = web.Response(text="download error", status=500)
        finally:
            try:
                self._add_cors_headers(resp)
            except Exception:
                pass
            return resp
