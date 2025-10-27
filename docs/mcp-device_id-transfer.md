# MCP设备ID传递功能使用指南

## 概述

MCP设备ID传递功能是小智ESP32语音助手的核心安全特性之一，通过加密方式安全传递设备ID（MAC地址）信息。

## 使用场景

如果您需要通过MCP传递设备ID，请按照本教程进行操作。如果不需要传递设备ID，可以忽略本教程。

**注意**：本教程适用于MCP接入点和服务端MCP通用场景。

## 配置指南

### 方式1：全模块部署

#### 1. 智控台密钥配置

1. 登录智控台
2. 进入"参数字典"页面的参数管理部分
3. 找到参数 `server.device_id_encrypt_key`
4. 输入用户自定义的加密密钥
5. 点击保存

### 方式2：单模块部署

#### 1. 配置文件密钥配置

在 `config.yaml` 配置文件中找到 `device_id_encrypt_key` 参数，并输入用户自定义的加密密钥。

**注意**：单模块部署的后续MCP工具集成配置与方式1完全相同。

#### 2. MCP工具集成配置（全模块部署和单模块部署通用）

1. 进入您要调用的MCP服务的代码目录
2. 在MCP工具的同级目录下创建 `auth.py` 文件
3. 复制粘贴以下代码到 `auth.py` 文件中：

```python
# auth.py 文件内容
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


def decrypt_device_id(encrypted_device_id: str, config: dict) -> str:
    """
    解密设备ID

    Args:
        encrypted_device_id: 加密的设备ID Token

    Returns:
        解密后的设备ID，如果解密失败返回None
    """
    print(f"encrypted_device_id: {encrypted_device_id}")

    device_id = None
    device_id_encrypt_key = config.get("device_id_encrypt_key")

    # 验证密钥和加密设备ID
    if (device_id_encrypt_key
        and encrypted_device_id
        and encrypted_device_id != "you need to set up device_id_encrypt_key"):

        try:
            auth = AuthToken(device_id_encrypt_key)
            is_valid, device_id = auth.verify_token(encrypted_device_id)

            if is_valid:
                print(f"解密成功，设备ID: {device_id}")
            else:
                print("device_id", device_id)
                print(f"Token验证失败或已过期")
                device_id = None

        except Exception as e:
            print(f"解密失败: {e}")
            device_id = None
    else:
        print(f"密钥未配置或encrypted_device_id无效")

    return device_id
```

4. 在MCP工具的代码文件开头导入解密函数：

```python
from auth import decrypt_device_id
```

5. 创建配置字典，填入与智控台中相同的密钥：

```python
config = {
    "device_id_encrypt_key": "你的mac地址加密密钥"
}
```

6. 在需要传递设备ID的MCP工具函数中添加参数 `encrypted_device_id: str`
7. 在函数中调用 `decrypt_device_id` 方法，并传递config参数：

```python
def your_mcp_function(encrypted_device_id: str, other_params):
    device_id = decrypt_device_id(encrypted_device_id, config)
    # 使用解密后的设备ID进行后续操作
    # ...
```

## 完整示例

### 示例：完整的MCP工具函数实现

```python
from fastmcp import FastMCP
from auth import decrypt_device_id


mcp = FastMCP("Device Info Server")

# 配置：设备ID加密密钥（必须与小智服务器config.yaml中的密钥相同）
config = {
    "device_id_encrypt_key": "test-key-12345" 
}


@mcp.tool()
async def get_device_id(encrypted_device_id: str) -> str:
    """获取设备ID(MAC地址)

    Args:
        encrypted_device_id: 加密的设备ID

    Returns:
        设备ID，格式为 XX:XX:XX:XX:XX:XX
    """
    # 解密设备ID
    device_id = decrypt_device_id(encrypted_device_id, config)

    if device_id:
        print(f"当前设备ID是: {device_id}")
        return f"设备ID: {device_id}"
    else:
        return "设备ID解密失败，无法获取设备ID"
    

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8077,
    )
```
