import os
import base64
from typing import Optional, Dict

import httpx

TAG = __name__


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"Device binding exception, bind code: {bind_code}")


class ManageApiClient:
    _instance = None
    _async_clients = {}  # Store independent clients for each event loop
    _secret = None

    def __new__(cls, config):
        """Singleton pattern ensures globally unique instance, and supports passing configuration parameters"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._init_client(config)
        return cls._instance

    @classmethod
    def _init_client(cls, config):
        """Initialize configuration (delay creating client)"""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("manager-api config error")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("manager-api url or secret config error")

        if "你" in cls.config.get("secret"):
            raise Exception("Please configure manager-api secret first")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6)  # Max retries
        cls.retry_delay = cls.config.get("retry_delay", 10)  # Initial retry delay (seconds)
        # Do not create AsyncClient here, delay until actual use
        cls._async_clients = {}

    @classmethod
    async def _ensure_async_client(cls):
        """Ensure async client is created (create independent client for each event loop)"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)

            # Create independent client for each event loop
            if loop_id not in cls._async_clients:
                # Server may actively close connection, httpx connection pool cannot detect and clean up correctly
                limits = httpx.Limits(
                    max_keepalive_connections=0,  # Disable keep-alive, create new connection every time
                )
                cls._async_clients[loop_id] = httpx.AsyncClient(
                    base_url=cls.config.get("url"),
                    headers={
                        "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                        "Accept": "application/json",
                        "Authorization": "Bearer " + cls._secret,
                    },
                    timeout=cls.config.get("timeout", 30),
                    limits=limits,  # Use limits
                )
            return cls._async_clients[loop_id]
        except RuntimeError:
            # If there is no running event loop, create a temporary one
            raise Exception("Must be called in async context")

    @classmethod
    async def _async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """Send single async HTTP request and handle response"""
        # Ensure client is created
        client = await cls._ensure_async_client()
        endpoint = endpoint.lstrip("/")
        response = None
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            result = response.json()

            # Handle business errors returned by API
            if result.get("code") == 10041:
                raise DeviceNotFoundException(result.get("msg"))
            elif result.get("code") == 10042:
                raise DeviceBindException(result.get("msg"))
            elif result.get("code") != 0:
                raise Exception(f"API returned error: {result.get('msg', 'Unknown error')}")

            # Return success data
            return result.get("data") if result.get("code") == 0 else None
        finally:
            # Ensure response is closed (executed even if exception occurs)
            if response is not None:
                await response.aclose()

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """Determine if exception should be retried"""
        # Network connection related errors
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # HTTP status code errors
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    async def _execute_async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """Async request executor with retry mechanism"""
        import asyncio

        retry_count = 0

        while retry_count <= cls.max_retries:
            try:
                # Execute async request
                return await cls._async_request(method, endpoint, **kwargs)
            except Exception as e:
                # Determine if retry is needed
                if retry_count < cls.max_retries and cls._should_retry(e):
                    retry_count += 1
                    print(
                        f"{method} {endpoint} async request failed, will retry for the {retry_count} time in {cls.retry_delay:.1f} seconds"
                    )
                    await asyncio.sleep(cls.retry_delay)
                    continue
                else:
                    # Do not retry, raise exception directly
                    raise

    @classmethod
    def safe_close(cls):
        """Safely close all async connection pools"""
        import asyncio

        for client in list(cls._async_clients.values()):
            try:
                asyncio.run(client.aclose())
            except Exception:
                pass
        cls._async_clients.clear()
        cls._instance = None


async def get_server_config() -> Optional[Dict]:
    """Get server base configuration"""
    return await ManageApiClient._instance._execute_async_request(
        "POST", "/config/server-base"
    )


async def get_agent_models(
    mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """Get agent model configuration"""
    return await ManageApiClient._instance._execute_async_request(
        "POST",
        "/config/agent-models",
        json={
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module,
        },
    )


async def generate_and_save_chat_summary(session_id: str) -> Optional[Dict]:
    """Generate and save chat summary"""
    try:
        return await ManageApiClient._instance._execute_async_request(
            "POST",
            f"/agent/chat-summary/{session_id}/save",
        )
    except Exception as e:
        print(f"Failed to generate and save chat summary: {e}")
        return None


async def report(
    mac_address: str, session_id: str, chat_type: int, content: str, audio, report_time
) -> Optional[Dict]:
    """Async chat history report"""
    if not content or not ManageApiClient._instance:
        return None
    try:
        return await ManageApiClient._instance._execute_async_request(
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
    except Exception as e:
        print(f"TTS report failed: {e}")
        return None


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
