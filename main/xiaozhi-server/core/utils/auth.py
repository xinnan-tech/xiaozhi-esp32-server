import jwt
import time
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64


class AuthToken:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()  # 转换为字节
        # 从密钥派生固定长度的加密密钥 (32字节 for AES-256)
        self.encryption_key = self._derive_key(32)

    def _derive_key(self, length: int) -> bytes:
        """派生固定长度的密钥"""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # 使用固定盐值（实际生产环境应使用随机盐）
        salt = b"fixed_salt_placeholder"  # 生产环境应改为随机生成
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(self.secret_key)

    def _encrypt_payload(self, payload: dict) -> str:
        """使用AES-GCM加密整个payload"""
        # 将payload转换为JSON字符串
        payload_json = json.dumps(payload)

        # 生成随机IV
        iv = os.urandom(12)
        # 创建加密器
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()

        # 加密并生成标签
        ciphertext = encryptor.update(payload_json.encode()) + encryptor.finalize()
        tag = encryptor.tag

        # 组合 IV + 密文 + 标签
        encrypted_data = iv + ciphertext + tag
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def _decrypt_payload(self, encrypted_data: str) -> dict:
        """解密AES-GCM加密的payload"""
        # 解码Base64
        data = base64.urlsafe_b64decode(encrypted_data.encode())
        # 拆分组件
        iv = data[:12]
        tag = data[-16:]
        ciphertext = data[12:-16]

        # 创建解密器
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(iv, tag),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()

        # 解密
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return json.loads(plaintext.decode())

    def generate_token(self, device_id: str) -> str:
        """
        生成JWT token
        :param device_id: 设备ID
        :return: JWT token字符串
        """
        # 设置过期时间为1小时后
        expire_time = datetime.now(timezone.utc) + timedelta(hours=1)

        # 创建原始payload
        payload = {"device_id": device_id, "exp": expire_time.timestamp()}

        # 加密整个payload
        encrypted_payload = self._encrypt_payload(payload)

        # 创建外层payload，包含加密数据
        outer_payload = {"data": encrypted_payload}

        # 使用JWT进行编码
        token = jwt.encode(outer_payload, self.secret_key, algorithm="HS256")
        return token

    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        验证token
        :param token: JWT token字符串
        :return: (是否有效, 设备ID)
        """
        try:
            # 先验证外层JWT（签名和过期时间）
            outer_payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # 解密内层payload
            inner_payload = self._decrypt_payload(outer_payload["data"])

            # 再次检查过期时间（双重验证）
            if inner_payload["exp"] < time.time():
                return False, None

            return True, inner_payload["device_id"]

        except jwt.InvalidTokenError:
            return False, None
        except json.JSONDecodeError:
            return False, None
        except Exception as e:  # 捕获其他可能的错误
            print(f"Token verification failed: {str(e)}")
            return False, None
