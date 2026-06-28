"""xiaozhi-server WebSocket 客户端 - 用于与 xiaozhi-server 通信"""

from typing import Optional

import httpx
from loguru import logger

from app.shared.config import settings


class XiaozhiClient:
    """xiaozhi-server HTTP/WS 客户端"""

    def __init__(self):
        self.base_url = settings.get("xiaozhi.http_url", "http://127.0.0.1:18003")
        self.ws_url = settings.get("xiaozhi.ws_url", "ws://127.0.0.1:18000/xiaozhi/v1/voice")

    async def get_device_config(self, device_id: str) -> Optional[dict]:
        """通过 xiaozhi-server 获取设备配置（agent 信息）"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试从 xiaozhi-server 获取设备配置
                resp = await client.get(
                    f"{self.base_url}/xiaozhi/ota/",
                    params={"device_id": device_id}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"获取设备配置失败: {e}")
        return None

    async def health_check(self) -> bool:
        """检查 xiaozhi-server 是否在线"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/")
                return resp.status_code == 200
        except Exception:
            return False
