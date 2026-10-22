import json
import time
import base64
import hashlib
import hmac
import os
import re
import glob
from typing import Dict, List, Tuple
from aiohttp import web

from core.auth import AuthManager
from core.utils.util import get_local_ip, get_vision_url
from core.api.base_handler import BaseHandler

TAG = __name__

# Device-Id 校验规则，与智控台 OTAController 使用同一套：
# 冒号 / 连字符 / 下划线分隔的 6 段 hex，或无分隔符的 12 位 hex
# 用 fullmatch 而不是自带锚点的正则：$ 会放过结尾的换行，两端接受范围就不一致了
DEVICE_ID_PATTERN = re.compile(
    r"([0-9A-Fa-f]{2}[:\-_]){5}[0-9A-Fa-f]{2}|[0-9A-Fa-f]{12}"
)

# Device-Model 会拼进 mqtt_client_id 进而参与密码签名，限制成不含
# 分隔符与通配符的字符，避免拼出畸形凭证
DEVICE_MODEL_PATTERN = re.compile(r"[A-Za-z0-9_\-]+")


def _normalize_device_id(device_id: str) -> str:
    """去掉分隔符转小写，让 aa:bb:cc:dd:ee:ff 与 aabbccddeeff 视为同一台设备"""
    return re.sub(r"[:\-_]", "", device_id).lower()


def _error_response(status: int, message: str) -> web.Response:
    """OTA 拒绝响应，状态码与智控台 /ota/ 保持一致，固件按状态码判断才不会走偏"""
    return web.Response(
        text=json.dumps({"success": False, "message": message}, separators=(",", ":")),
        content_type="application/json",
        status=status,
    )


def _parse_activation_codes(raw_codes) -> Dict[str, str | None]:
    """解析 activation_codes 成 码 -> 绑定的 Device-Id，不绑定时值为 None

    支持两种写法：裸字符串表示不限设备，"码: Device-Id" 表示只能用这台设备换。
    码本身不能带冒号，冒号只作分隔用。
    """
    codes: Dict[str, str | None] = {}
    for raw in raw_codes:
        code, _, bound_device = str(raw).partition(":")
        code = code.strip()
        if code:
            codes[code] = bound_device.strip() or None
    return codes


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
        self._load_auth_config(config)

        # firmware storage
        self.bin_dir = os.path.join(os.getcwd(), "data", "bin")
        # cache structure: { 'updated_at': timestamp, 'ttl': seconds, 'files_by_model': { model: [(version, filename), ...] } }
        self._bin_cache: Dict = {
            "updated_at": 0,
            "ttl": config.get("firmware_cache_ttl", 30),
            "files_by_model": {},
        }

    def _load_auth_config(self, config: dict):
        """从配置加载认证相关属性，改配置后可重复调用"""
        auth_config = config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # 设备白名单：命中白名单只影响 token 有效期，不再跳过 token 校验
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        # 白名单设备的 token 有效期，默认与普通设备一致
        self.allowed_expire_seconds = auth_config.get(
            "allowed_devices_expire_seconds", None
        )
        # 白名单设备首次接入免凭证自举一次，否则升级后没有任何换凭证的入口
        self.allowed_bootstrap = auth_config.get("allowed_devices_bootstrap", True)
        self.allowed_bootstrapped = set()
        # 一次性激活码，供无 token 的设备首次绑定；写 "码: Device-Id" 可绑到具体设备
        self.activation_codes = _parse_activation_codes(
            auth_config.get("activation_codes", []) or []
        )
        secret_key = config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds")
        issued_after = auth_config.get("issued_after", 0)
        self.auth = AuthManager(
            secret_key=secret_key,
            expire_seconds=expire_seconds,
            issued_after=issued_after,
        )
        self._warn_if_locked_out()

    def _warn_if_locked_out(self):
        """存量白名单设备升级后若没有换凭证的入口会直接掉线，启动时说清楚"""
        if not self.auth_enable:
            return
        if not self.allowed_devices:
            return
        if self.allowed_bootstrap or self.activation_codes:
            return
        self.logger.bind(tag=TAG).warning(
            "配置了 allowed_devices 但既没开 allowed_devices_bootstrap 也没有 "
            "activation_codes：这些白名单设备升级后没有凭证来源，会连不上。"
            "请在 config.yaml 的 server.auth 里加一个 activation_codes，"
            "或把 allowed_devices_bootstrap 设回 true"
        )

    def _expire_for(self, device_id: str):
        """白名单设备的 token 有效期，其余设备沿用默认"""
        if self.allowed_devices and device_id in self.allowed_devices:
            return self.allowed_expire_seconds
        return None

    def _issue_ws_token(self, request, client_id: str, device_id: str) -> Tuple:
        """校验 OTA 凭证并签发 websocket token。

        返回 (token, 待作废的激活码)，无有效凭证时返回 ("", "")。
        激活码不在这里作废，交给调用方在响应组装成功后回收，中途失败不烧凭证。
        """
        auth_header = request.headers.get("Authorization", "")
        presented = auth_header[7:] if auth_header.startswith("Bearer ") else ""
        if not presented:
            return self._bootstrap_whitelisted(device_id, client_id), ""

        if self.auth.verify_token(
            presented,
            client_id=client_id,
            username=device_id,
            expire_seconds=self._expire_for(device_id),
        ):
            return self.auth.generate_token(client_id, device_id), ""

        if self._matches_activation_code(presented, device_id):
            return self.auth.generate_token(client_id, device_id), presented

        return "", ""

    def _bootstrap_whitelisted(self, device_id: str, client_id: str) -> str:
        """白名单设备首次接入免凭证换 token，每台设备只放行一次

        白名单是运维在配置里显式列出的可信 MAC，不接受任何上报值，
        也不新增信任来源；这里只是让升级前免 token 的存量设备换到凭证，
        否则白名单去掉旁路后它们升级即掉线。之后必须带 token。
        """
        if not (
            self.allowed_bootstrap
            and self.allowed_devices
            and device_id in self.allowed_devices
            and device_id not in self.allowed_bootstrapped
        ):
            return ""
        self.allowed_bootstrapped.add(device_id)
        self.logger.bind(tag=TAG).warning(
            f"白名单设备免凭证自举签发 token: {device_id}，此后该设备必须携带凭证"
        )
        return self.auth.generate_token(client_id, device_id)

    def _matches_activation_code(self, presented: str, device_id: str) -> bool:
        """激活码若绑定了设备，必须与上报的 Device-Id 一致"""
        if presented not in self.activation_codes:
            return False
        bound_device = self.activation_codes[presented]
        if not bound_device:
            return True
        return _normalize_device_id(bound_device) == _normalize_device_id(device_id)

    def _consume_activation_code(self, presented: str) -> None:
        """作废一次性激活码，只在响应组装成功后调用"""
        self.activation_codes.pop(presented, None)
        self.logger.bind(tag=TAG).info("激活码已使用并作废，设备完成首次绑定")

    def _is_valid_device_id(self, device_id: str) -> bool:
        """Device-Id 会被拼进 MQTT topic，格式校验与智控台用同一套规则"""
        return bool(DEVICE_ID_PATTERN.fullmatch(device_id))

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

    def generate_password_signature(self, content: str, secret_key: str) -> str:
        """生成MQTT密码签名

        Args:
            content: 签名内容 (clientId + '|' + username)
            secret_key: 密钥

        Returns:
            str: Base64编码的HMAC-SHA256签名
        """
        try:
            hmac_obj = hmac.new(
                secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
            )
            signature = hmac_obj.digest()
            return base64.b64encode(signature).decode("utf-8")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"生成MQTT密码签名失败: {e}")
            return ""

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
            # OTA 请求开始携带 token 和一次性激活码，凭证不进日志
            safe_headers = {
                k: ("***" if k.lower() == "authorization" else v)
                for k, v in request.headers.items()
            }
            self.logger.bind(tag=TAG).debug(f"OTA请求头: {safe_headers}")
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

            # 开启认证时，MQTT 与 WebSocket 两条下发路径都必须先通过凭证校验
            ws_token = ""
            activation_code = ""
            if self.auth_enable:
                ws_token, activation_code = self._issue_ws_token(
                    request, client_id, device_id
                )
                if not ws_token:
                    self.logger.bind(tag=TAG).warning(
                        f"OTA请求凭证无效: device_id={device_id}"
                    )
                    response = _error_response(401, "invalid credential")
                    return response

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

            # existing mqtt/websocket logic (unchanged)
            mqtt_gateway_endpoint = server_config.get("mqtt_gateway")

            if mqtt_gateway_endpoint:  # 如果配置了非空字符串
                # 下面两个值都会拼进 MQTT 凭证，只在真下发 MQTT 时才校验，
                # 免得不开 MQTT 的部署被无端拦下
                if not self._is_valid_device_id(device_id):
                    self.logger.bind(tag=TAG).warning(
                        f"OTA请求设备ID格式非法: {device_id}"
                    )
                    response = _error_response(400, "invalid device-id")
                    return response
                if not DEVICE_MODEL_PATTERN.fullmatch(device_model):
                    self.logger.bind(tag=TAG).warning(
                        f"OTA请求设备型号格式非法: {device_model}"
                    )
                    response = _error_response(400, "invalid device-model")
                    return response

                group_id = f"GID_{device_model}"

                mac_address_safe = device_id.replace(":", "_")
                mqtt_client_id = f"{group_id}@@@{mac_address_safe}@@@{mac_address_safe}"

                # 构建用户数据
                user_data = {"ip": "unknown"}
                try:
                    user_data_json = json.dumps(user_data)
                    username = base64.b64encode(user_data_json.encode("utf-8")).decode(
                        "utf-8"
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"生成用户名失败: {e}")
                    username = ""

                # 生成密码
                password = ""
                signature_key = server_config.get("mqtt_signature_key", "")
                if signature_key:
                    password = self.generate_password_signature(
                        mqtt_client_id + "|" + username, signature_key
                    )
                    if not password:
                        password = ""  # 签名失败则留空，由设备决定是否允许无密码
                else:
                    self.logger.bind(tag=TAG).warning("缺少MQTT签名密钥，密码留空")

                # 构建MQTT配置（直接使用 mqtt_gateway 字符串）
                return_json["mqtt"] = {
                    "endpoint": mqtt_gateway_endpoint,
                    "client_id": mqtt_client_id,
                    "username": username,
                    "password": password,
                    "publish_topic": "device-server",
                    "subscribe_topic": f"devices/p2p/{mac_address_safe}",
                }
                self.logger.bind(tag=TAG).info(f"为设备 {device_id} 下发MQTT网关配置")

            else:  # 未配置 mqtt_gateway，下发 WebSocket
                # token 已在入口处完成凭证校验，认证关闭时保持不下发
                token = ws_token
                # NOTE: use websocket_port here
                return_json["websocket"] = {
                    "url": self._get_websocket_url(local_ip, websocket_port),
                    "token": token,
                }
                self.logger.bind(tag=TAG).info(
                    f"未配置MQTT网关，为设备 {device_id} 下发WebSocket配置"
                )

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
            # 响应已经组装成功，这时才作废激活码，中途出错不烧凭证
            if activation_code:
                self._consume_activation_code(activation_code)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA POST处理异常: {e}")
            return_json = {"success": False, "message": "request error."}
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response, request)
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
            self._add_cors_headers(response, request)
            return response

    async def handle_download(self, request):
        """
        下载固件接口
        URL: /xiaozhi/ota/download/{filename}
        - 只允许下载 data/bin 目录下的 .bin 文件
        - filename 必须是 basename 且匹配安全的模式
        - 开启认证时需携带与 OTA 请求一致的凭证
        """
        try:
            if self.auth_enable:
                device_id = request.headers.get("Device-Id", "")
                client_id = request.headers.get("Client-Id", "")
                auth_header = request.headers.get("Authorization", "")
                token = (
                    auth_header[7:] if auth_header.startswith("Bearer ") else ""
                )
                authorized = (
                    device_id
                    and client_id
                    and token
                    and self.auth.verify_token(
                        token,
                        client_id=client_id,
                        username=device_id,
                        expire_seconds=self._expire_for(device_id),
                    )
                )
                if not authorized:
                    self.logger.bind(tag=TAG).warning(
                        f"固件下载凭证无效: device_id={device_id}"
                    )
                    raise web.HTTPUnauthorized(text="unauthorized")

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
                self._add_cors_headers(resp, request)
            except Exception:
                pass
            return resp
