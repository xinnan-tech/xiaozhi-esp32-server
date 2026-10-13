import os
import base64
import asyncio
import functools
import threading
import traceback
from typing import Optional, Dict

import httpx

TAG = __name__

# _retry_wait 的分片粒度：safe_close 后 ~100ms 内收尾，轮询开销可忽略
_RETRY_WAIT_SLICE = 0.1


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"设备绑定异常，绑定码: {bind_code}")


class ManageApiShutdownError(Exception):
    """safe_close 打断重试等待后的收尾异常，__cause__ 保留最后一次失败原因。"""


class ManageApiClient:
    _instance = None
    _instance_lock = threading.Lock()  # 保护 _instance 与 _closed 的读写
    _secret = None
    _closed = False  # safe_close() 后置为 True，关闭后不再创建新连接

    def __new__(cls, config):
        """单例模式确保全局唯一实例，并支持传入配置参数"""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._init_client(config)
            return cls._instance

    @classmethod
    def _init_client(cls, config):
        """初始化配置（延迟创建客户端）"""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("manager-api配置错误")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("manager-api的url或secret配置错误")

        if "你" in cls.config.get("secret"):
            raise Exception("请先配置manager-api的secret")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6)  # 最大重试次数
        cls.retry_delay = cls.config.get("retry_delay", 10)  # 初始重试延迟(秒)
        # 不在这里创建 AsyncClient，延迟到实际使用时创建
        cls._closed = False

    @classmethod
    def _build_client(cls) -> httpx.AsyncClient:
        """构造单次业务请求（含重试）专用的 AsyncClient。

        约束：由调用方 ``async with`` 在同一 loop 内关闭，禁止跨请求缓存；构造在锁外执行，避免并发请求阻塞事件循环。
        """
        with cls._instance_lock:
            if cls._closed:
                raise Exception("ManageApiClient已关闭，不再创建新的HTTP客户端")
            base_url = cls.config.get("url")
            secret = cls._secret
            timeout = cls.config.get("timeout", 30)
        return httpx.AsyncClient(
            base_url=base_url,
            headers={
                "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                "Accept": "application/json",
                "Authorization": "Bearer " + secret,
            },
            timeout=timeout,
            # 连接复用仅限本次请求；keepalive_expiry 动态覆盖 retry_delay，
            # 防止重试等待期间池内连接过期。
            limits=httpx.Limits(
                max_keepalive_connections=1,
                keepalive_expiry=max(30, cls.retry_delay + 5),
            ),
            trust_env=False,
            # verify=True 现建 context：httpcore 建连会原地改写传入
            # context（无锁），共享单例并发握手有竞态。
            verify=True,
        )

    @classmethod
    async def _async_request(
        cls, client: httpx.AsyncClient, method: str, endpoint: str, **kwargs
    ) -> Dict:
        """在给定 client 上执行单次请求；响应读取后立即释放回连接池。"""
        endpoint = endpoint.lstrip("/")
        response = None
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            result = response.json()
            if result.get("code") == 10041:
                raise DeviceNotFoundException(result.get("msg"))
            elif result.get("code") == 10042:
                raise DeviceBindException(result.get("msg"))
            elif result.get("code") != 0:
                raise Exception(f"API返回错误: {result.get('msg', '未知错误')}")
            return result.get("data")
        finally:
            if response is not None:
                try:
                    await response.aclose()
                except Exception:
                    # 约束：必须吞掉释放异常，避免覆盖业务异常、破坏重试判断
                    pass

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """判断异常是否应该重试"""
        # 网络连接相关错误
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # RPE 仅"without sending a response"（响应未开始，安全）变体重试；
        # 截断变体可能已处理请求会重复提交，文案变更时退化为不重试。
        if isinstance(exception, httpx.RemoteProtocolError):
            return "without sending a response" in str(exception)

        # HTTP状态码错误
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    async def _retry_wait(cls):
        """可被 safe_close() 打断的重试等待（100ms 分片轮询 _closed）。

        约束：不得一次睡满 retry_delay，否则关闭后收尾要拖满整个重试周期。
        """
        remaining = cls.retry_delay
        while remaining > 0 and not cls._closed:
            step = min(_RETRY_WAIT_SLICE, remaining)
            await asyncio.sleep(step)
            remaining -= step

    @classmethod
    async def _execute_async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """带重试机制的业务请求执行器。

        约束：client 整个重试过程只构造一次，结束后由 ``async with`` 关闭；safe_close 不取消已开始的尝试，只打断重试等待（抛 ManageApiShutdownError）。
        """
        client = cls._build_client()
        async with client:
            retry_count = 0

            while retry_count <= cls.max_retries:
                try:
                    # 执行异步请求
                    return await cls._async_request(client, method, endpoint, **kwargs)
                except Exception as e:
                    # 判断是否应该重试
                    if retry_count < cls.max_retries and cls._should_retry(e):
                        retry_count += 1
                        print(
                            f"{method} {endpoint} 异步请求失败，将在 {cls.retry_delay:.1f} 秒后进行第 {retry_count} 次重试"
                        )
                        await cls._retry_wait()
                        if cls._closed:
                            # 收尾必须可区分：裸 raise 会把 shutdown 早退伪装
                            # 成网络抖动，掩盖服务下线信号
                            raise ManageApiShutdownError(
                                f"safe_close 已打断重试等待: {e}") from e
                        continue
                    else:
                        # 不重试，直接抛出异常
                        raise

    @classmethod
    def _get_instance(cls) -> Optional["ManageApiClient"]:
        """线程安全地获取单例实例引用。

        约束：调用方必须持有返回的局部引用，禁止判空后重读 _instance（TOCTOU 窗口）。
        """
        with cls._instance_lock:
            return cls._instance

    @classmethod
    def safe_close(cls):
        """关闭请求入口；在途请求在各自事件循环中释放客户端。

        已开始的请求不取消；重试等待被打断、跳过剩余重试（见 _retry_wait）。
        """
        with cls._instance_lock:
            cls._closed = True
            cls._instance = None


def api_guard(error_msg: str = None, raise_when_closed: bool = False):
    """装饰器：统一获取单例实例、判空与异常兜底

    - 通过 _get_instance() 一次性获取实例局部引用，注入为被装饰函数的
      第一个参数，消除与 safe_close() 之间的 TOCTOU 竞态窗口；
    - 实例未初始化或已关闭时：raise_when_closed=True 抛出明确异常
      （用于启动路径函数），否则静默返回 None（用于守护线程路径）；
    - error_msg 不为 None 时捕获请求异常、打印日志并返回 None；
      为 None 时异常原样抛出，由调用方处理。
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            instance = ManageApiClient._get_instance()
            if instance is None:
                if raise_when_closed:
                    raise Exception("ManageApiClient未初始化或已关闭")
                return None
            if error_msg is None:
                return await func(instance, *args, **kwargs)
            try:
                return await func(instance, *args, **kwargs)
            except Exception as e:
                # 约束：httpx / 解析异常打全堆栈；业务语义异常只打
                # message（消息自带上下文，堆栈是高频噪声）
                if isinstance(e, (httpx.HTTPError, ValueError)):
                    print(f"{error_msg}: {e}\n{traceback.format_exc()}")
                else:
                    print(f"{error_msg}: {e}")
                return None

        return wrapper

    return decorator


@api_guard(raise_when_closed=True)
async def get_server_config(instance) -> Optional[Dict]:
    """获取服务器基础配置"""
    return await instance._execute_async_request("POST", "/config/server-base")


@api_guard(raise_when_closed=True)
async def get_agent_models(
    instance, mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """获取代理模型配置"""
    return await instance._execute_async_request(
        "POST",
        "/config/agent-models",
        json={
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module,
        },
    )


@api_guard("获取替换词失败")
async def get_correct_words(instance, mac_address: str) -> Optional[Dict]:
    """获取智能体替换词"""
    return await instance._execute_async_request(
        "POST", "/config/correct-words",
        json={"macAddress": mac_address}
    )


@api_guard("生成并保存聊天记录总结失败")
async def generate_and_save_chat_summary(instance, session_id: str) -> Optional[Dict]:
    """生成并保存聊天记录总结（守护线程中调用，服务已关闭时静默返回 None）"""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-summary/{session_id}/save",
    )


@api_guard("生成并保存聊天标题失败")
async def generate_and_save_chat_title(instance, session_id: str) -> Optional[Dict]:
    """生成并保存聊天标题（守护线程中调用，服务已关闭时静默返回 None）"""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-title/{session_id}/generate",
    )


@api_guard("TTS上报失败")
async def report(
    instance, mac_address: str, session_id: str, chat_type: int, content: str, audio, report_time
) -> Optional[Dict]:
    """异步聊天记录上报"""
    if not content:
        return None
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-history/report",
        json={
            "macAddress": mac_address,
            "sessionId": session_id,
            "chatType": chat_type,
            "content": content,
            "reportTime": report_time,
            "audioBase64": (
                base64.b64encode(audio).decode("utf-8") if audio else None
            ),
        },
    )


@api_guard("通讯录查找失败")
async def lookup_address_book(instance, caller_mac: str, nickname: str) -> Optional[Dict]:
    """根据昵称查找目标设备"""
    return await instance._execute_async_request(
        "GET",
        f"/device/address-book/lookup?callerMac={caller_mac}&nickname={nickname}",
    )


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
