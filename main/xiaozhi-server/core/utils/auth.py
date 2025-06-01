import jwt
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


class AuthToken:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def generate_token(self, device_id: str) -> str:
        """
        生成JWT token
        :param device_id: 设备ID
        :return: JWT token字符串
        """
        # 设置过期时间为1小时后
        expire_time = datetime.now(timezone.utc) + timedelta(hours=1)

        # 创建payload
        payload = {"device_id": device_id, "exp": expire_time.timestamp()}

        # 使用JWT进行编码
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return token

    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        验证token
        :param token: JWT token字符串
        :return: (是否有效, 设备ID)
        """
        try:
            # 解码token
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # 检查是否过期
            if payload["exp"] < time.time():
                return False, None

            return True, payload["device_id"]
        except jwt.InvalidTokenError:
            return False, None
