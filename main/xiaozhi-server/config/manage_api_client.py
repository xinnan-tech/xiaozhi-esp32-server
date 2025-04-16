import os
from typing import Optional, Dict
import httpx

TAG = __name__


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"设备绑定异常，绑定码: {bind_code}")


class ManageApiClient:
    _instance = None
    _client = None
    _secret = None

    def __new__(cls, config):
        """单例模式确保全局唯一实例，并支持传入配置参数"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._init_client(config)
        return cls._instance

    @classmethod
    def _init_client(cls, config):
        """初始化持久化连接池"""
        cls.config = config.get('manager-api')

        if not cls.config:
            raise Exception("manager-api配置错误")

        if not cls.config.get('url') or not cls.config.get('secret'):
            raise Exception("manager-api的url或secret配置错误")

        if "你" in cls.config.get('secret'):
            raise Exception("请先配置manager-api的secret")

        cls._secret = cls.config.get('secret')
        # NOTE(goody): 2025/4/16 http相关资源统一管理，后续可以增加线程池或者超时
        # 后续也可以统一配置apiToken之类的走通用的Auth
        cls._client = httpx.Client(
            base_url=cls.config.get('url'),
            headers={
                "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                "Accept": "application/json"
            },
        )

    @classmethod
    def _execute_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """增强型请求执行器"""
        try:
            response = cls._client.request(
                method,
                endpoint.lstrip("/"),
                **kwargs
            )
            response.raise_for_status()
            result = response.json()
            if result.get("code") == 10041:
                raise DeviceNotFoundException(result.get("msg"))
            elif result.get("code") == 10042:
                raise DeviceBindException(result.get("msg"))
            elif result.get("code") != 0:
                raise Exception(f"API返回错误: {result.get('msg', '未知错误')}")
            if result.get("code") == 0:
                return result["data"]
            return None
        except Exception as e:
            raise

    @classmethod
    def safe_close(cls):
        """安全关闭连接池"""
        if cls._client:
            cls._client.close()
            cls._instance = None


def get_server_config() -> Optional[Dict]:
    """获取服务器基础配置"""
    return ManageApiClient._instance._execute_request(
        "POST",
        "/config/server-base",
        json={
            "secret": ManageApiClient._secret
        }
    )


def get_agent_models(mac_address: str, client_id: str, selected_module: Dict) -> Optional[Dict]:
    """获取代理模型配置"""
    return ManageApiClient._instance._execute_request(
        "POST",
        "/config/agent-models",
        json={
            "secret": ManageApiClient._secret,
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module
        }
    )


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
