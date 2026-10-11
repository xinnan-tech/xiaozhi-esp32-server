import os
import base64
import functools
import threading
from typing import Optional, Dict

import httpx

TAG = __name__


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"Device bind error, bind code: {bind_code}")


class ManageApiClient:
    _instance = None
    _instance_lock = threading.Lock()
    _async_clients = {}  # One client per event loop
    _secret = None
    _closed = False  # Set to True after safe_close(); no new connections will be created after closure.

    def __new__(cls, config):
        """Singleton ensures a single global instance and supports config injection."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._init_client(config)
            return cls._instance

    @classmethod
    def _init_client(cls, config):
        """Initialize configuration (client creation is deferred)."""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("manager-api configuration is missing")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("manager-api url or secret is invalid")

        if "your_" in cls.config.get("secret", "").lower():
            raise Exception("Please configure manager-api secret first")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6)  # Max retries
        cls.retry_delay = cls.config.get("retry_delay", 10)  # Initial retry delay (seconds)
        # Defer AsyncClient creation until first use
        cls._async_clients = {}
        cls._closed = False

    @classmethod
    async def _ensure_async_client(cls):
        """Ensure async client exists (one per event loop)."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)

            with cls._instance_lock:
                if cls._closed:
                    raise Exception("ManageApiClient is closed; no new HTTP client can be created")
                if loop_id not in cls._async_clients:
                    limits = httpx.Limits(max_keepalive_connections=0)
                    cls._async_clients[loop_id] = httpx.AsyncClient(
                        base_url=cls.config.get("url"),
                        headers={
                            "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                            "Accept": "application/json",
                            "Authorization": "Bearer " + cls._secret,
                        },
                        timeout=cls.config.get("timeout", 30),
                        limits=limits,
                        trust_env=False,
                    )
                return cls._async_clients[loop_id]
        except RuntimeError:
            # No running loop
            raise Exception("Must be called from an async context")

    @classmethod
    async def _async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """Send a single async HTTP request and process the response."""
        # Ensure client exists
        client = await cls._ensure_async_client()
        endpoint = endpoint.lstrip("/")
        response = None
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            result = response.json()

            # Handle API business errors
            if result.get("code") == 10041:
                raise DeviceNotFoundException(result.get("msg"))
            elif result.get("code") == 10042:
                raise DeviceBindException(result.get("msg"))
            elif result.get("code") != 0:
                raise Exception(f"API error: {result.get('msg', 'Unknown error')}")

            # Return success data
            return result.get("data") if result.get("code") == 0 else None
        finally:
            # Ensure response is closed (even on exceptions)
            if response is not None:
                await response.aclose()

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """Determine whether an exception should trigger retry."""
        # Network-related errors
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # HTTP status errors
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    async def _execute_async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """Async request executor with retries."""
        import asyncio

        retry_count = 0

        while retry_count <= cls.max_retries:
            try:
                # Execute request
                return await cls._async_request(method, endpoint, **kwargs)
            except Exception as e:
                # Decide whether to retry
                if retry_count < cls.max_retries and cls._should_retry(e):
                    retry_count += 1
                    print(
                        f"{method} {endpoint} async request failed. Retrying in {cls.retry_delay:.1f}s (attempt {retry_count})"
                    )
                    await asyncio.sleep(cls.retry_delay)
                    continue
                else:
                    # No retry; re-raise
                    raise

    @classmethod
    def _get_instance(cls):
        """Thread-safely get singleton instance reference

        Callers should use the returned local reference instead of re-reading after null check
        ManageApiClient._instance: even if safe_close() subsequently sets _instance
        Set to None; the acquired reference still points to the original object, eliminating the "null check after,
        Use TOCTOU race window where previous instance was nullified
        """
        with cls._instance_lock:
            return cls._instance

    @classmethod
    def safe_close(cls):
        """Safely close all async connection pools."""
        import asyncio

        with cls._instance_lock:
            cls._closed = True
            clients = list(cls._async_clients.values())
            cls._async_clients.clear()
            cls._instance = None

        for client in clients:
            try:
                asyncio.run(client.aclose())
            except Exception:
                pass


def api_guard(error_msg: str = None, raise_when_closed: bool = False):
    """Inject a stable client instance and avoid shutdown races for API calls."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            instance = ManageApiClient._get_instance()
            if instance is None:
                if raise_when_closed:
                    raise Exception("ManageApiClient is not initialized or has been closed")
                return None
            if error_msg is None:
                return await func(instance, *args, **kwargs)
            try:
                return await func(instance, *args, **kwargs)
            except Exception as exc:
                print(f"{error_msg}: {exc}")
                return None
        return wrapper
    return decorator


@api_guard(raise_when_closed=True)
async def get_server_config(instance) -> Optional[Dict]:
    """Fetch server base config."""
    return await instance._execute_async_request(
        "POST", "/config/server-base"
    )


@api_guard(raise_when_closed=True)
async def get_agent_models(
    instance, mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """Fetch agent model config."""
    return await instance._execute_async_request(
        "POST",
        "/config/agent-models",
        json={
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module,
        },
    )


@api_guard("Failed to get correction words")
async def get_correct_words(instance, mac_address: str) -> Optional[Dict]:
    """Fetch agent correction words."""
    return await instance._execute_async_request(
        "POST", "/config/correct-words",
        json={"macAddress": mac_address}
    )


@api_guard("Failed to generate and save chat summary")
async def generate_and_save_chat_summary(instance, session_id: str) -> Optional[Dict]:
    """Generate and save chat summary."""
    return await instance._execute_async_request("POST", f"/agent/chat-summary/{session_id}/save")


@api_guard("Failed to generate and save chat title")
async def generate_and_save_chat_title(instance, session_id: str) -> Optional[Dict]:
    """Generate and save a chat title."""
    return await instance._execute_async_request("POST", f"/agent/chat-title/{session_id}/generate")


@api_guard("TTS report failed")
async def report(
    instance, mac_address: str, session_id: str, chat_type: int, content: str, audio, report_time
) -> Optional[Dict]:
    """Async chat history report."""
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


@api_guard("Address-book lookup failed")
async def lookup_address_book(instance, caller_mac: str, nickname: str) -> Optional[Dict]:
    """Look up a target device by nickname."""
    return await instance._execute_async_request(
        "GET",
        f"/device/address-book/lookup?callerMac={caller_mac}&nickname={nickname}",
    )


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
