import hmac
import base64
import hashlib
import time


class AuthenticationError(Exception):
    """认证异常"""

    pass


class AuthMiddleware:
    """
    认证中间件
    用于 WebSocket/MQTT 连接认证
    集成 AuthManager 的 token 验证逻辑，支持多种认证方式
    """

    def __init__(self, config: dict):
        """
        初始化认证中间件
        
        Args:
            config: 配置字典，包含认证相关配置
        """
        self.config = config
        server_config = config.get("server", {})
        auth_config = server_config.get("auth", {})
        
        self.enabled = auth_config.get("enabled", False)
        self.tokens = auth_config.get("tokens", [])
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        
        # 获取 auth_key 用于 HMAC token 验证
        self.auth_key = server_config.get("auth_key", "")
        expire_seconds = auth_config.get("expire_seconds", None)
        
        # 创建 AuthManager 实例用于 HMAC token 验证
        if self.auth_key:
            self._auth_manager = AuthManager(
                secret_key=self.auth_key,
                expire_seconds=expire_seconds
            )
        else:
            self._auth_manager = None

    def authenticate(self, device_id: str, token: str = None, client_id: str = None) -> bool:
        """
        验证设备认证（同步方法）
        
        Args:
            device_id: 设备 ID
            token: 认证令牌（可以是静态 token 或 HMAC token）
            client_id: 客户端 ID（用于 HMAC token 验证）
            
        Returns:
            bool: 认证是否通过
        """
        if not self.enabled:
            return True
        
        # 1. 检查白名单
        if device_id and device_id in self.allowed_devices:
            return True
        
        # 2. 检查静态 token
        if token:
            # 移除 Bearer 前缀（如果有）
            if token.startswith("Bearer "):
                token = token[7:]
            
            for token_config in self.tokens:
                if token_config.get("token") == token:
                    return True
        
        # 3. 检查 HMAC token（需要 AuthManager）
        if token and self._auth_manager and client_id and device_id:
            if self._auth_manager.verify_token(token, client_id, device_id):
                return True
        
        return False

    async def authenticate_async(self, headers: dict) -> bool:
        """
        从 headers 中提取信息并进行异步认证
        
        Args:
            headers: HTTP 请求头字典
            
        Returns:
            bool: 认证是否通过
            
        Raises:
            AuthenticationError: 认证失败时抛出
        """
        if not self.enabled:
            return True
        
        device_id = headers.get("device-id")
        client_id = headers.get("client-id")
        authorization = headers.get("authorization", "")
        
        # 提取 token
        token = None
        if authorization:
            if authorization.startswith("Bearer "):
                token = authorization[7:]
            else:
                token = authorization
        
        # 执行认证
        if self.authenticate(device_id, token, client_id):
            return True
        
        raise AuthenticationError(f"认证失败: device_id={device_id}")

    def authenticate_websocket(self, websocket) -> bool:
        """
        WebSocket 连接认证
        
        Args:
            websocket: WebSocket 连接对象
            
        Returns:
            bool: 认证是否通过
        """
        if not self.enabled:
            return True
        
        headers = dict(websocket.request.headers)
        device_id = headers.get("device-id")
        client_id = headers.get("client-id")
        authorization = headers.get("authorization", "")
        
        # 提取 token
        token = None
        if authorization:
            if authorization.startswith("Bearer "):
                token = authorization[7:]
            else:
                token = authorization
        
        return self.authenticate(device_id, token, client_id)


class AuthManager:
    """
    统一授权认证管理器
    生成与验证 client_id device_id token（HMAC-SHA256）认证三元组
    token 中不含明文 client_id/device_id，只携带签名 + 时间戳; client_id/device_id在连接时传递
    在 MQTT 中 client_id: client_id, username: device_id, password: token
    在 Websocket 中，header:{Device-ID: device_id, Client-ID: client_id, Authorization: Bearer token, ......}
    """

    def __init__(self, secret_key: str, expire_seconds: int = 60 * 60 * 24 * 30):
        if not expire_seconds or expire_seconds < 0:
            self.expire_seconds = 60 * 60 * 24 * 30
        else:
            self.expire_seconds = expire_seconds
        self.secret_key = secret_key

    def _sign(self, content: str) -> str:
        """HMAC-SHA256签名并Base64编码"""
        sig = hmac.new(
            self.secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    def generate_token(self, client_id: str, username: str) -> str:
        """
        生成 token
        Args:
            client_id: 设备连接ID
            username: 设备用户名（通常为deviceId）
        Returns:
            str: token字符串
        """
        ts = int(time.time())
        content = f"{client_id}|{username}|{ts}"
        signature = self._sign(content)
        # token仅包含签名与时间戳，不包含明文信息
        token = f"{signature}.{ts}"
        return token

    def verify_token(self, token: str, client_id: str, username: str) -> bool:
        """
        验证token有效性
        Args:
            token: 客户端传入的token
            client_id: 连接使用的client_id
            username: 连接使用的username
        """
        try:
            sig_part, ts_str = token.split(".")
            ts = int(ts_str)
            if int(time.time()) - ts > self.expire_seconds:
                return False  # 过期

            expected_sig = self._sign(f"{client_id}|{username}|{ts}")
            if not hmac.compare_digest(sig_part, expected_sig):
                return False

            return True
        except Exception:
            return False
