import os
import base64
import asyncio
import functools
import threading
import traceback
from typing import Optional, Dict

import httpx

TAG = __name__

# _retry_wait slice granularity: after safe_close we finish within ~100ms; polling overhead is negligible
_RETRY_WAIT_SLICE = 0.1


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"Device binding exception, Binding code: {bind_code}")


class ManageApiShutdownError(Exception):
    """Terminal error raised when safe_close interrupts a retry wait; __cause__ keeps the last failure reason."""


class ManageApiClient:
    _instance = None
    _instance_lock = threading.Lock() # guards reads/writes of _instance and _closed
    _secret = None
    _closed = False # set to True by safe_close(); no new connections are created after closing

    def __new__(cls, config):
        """Singleton pattern ensures a globally unique instance and supports passing config parameters."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._init_client(config)
            return cls._instance

    @classmethod
    def _init_client(cls, config):
        """Initialize configuration (lazy client creation)"""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("manager-api configuration error")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("manager-api url or secret configuration error")

        if "your_" in cls.config.get("secret", "").lower():
            raise Exception("Please configure the manager-api secret first")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6) # Maximum retry count
        cls.retry_delay = cls.config.get("retry_delay", 10) # Initial retry delay(seconds)
        # Do not create the AsyncClient here; defer creation until actually used
        cls._closed = False

    @classmethod
    def _build_client(cls) -> httpx.AsyncClient:
        """Build the AsyncClient dedicated to one business request (including its retries).

        Constraint: the caller closes it via ``async with`` inside the same loop; caching across requests is prohibited; construction happens outside the lock so concurrent requests do not block the event loop.
        """
        with cls._instance_lock:
            if cls._closed:
                raise Exception("ManageApiClient is closed; no new HTTP client is created")
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
            # Connection reuse is limited to this request; keepalive_expiry dynamically covers retry_delay,
            # preventing pooled connections from expiring during retry waits.
            limits=httpx.Limits(
                max_keepalive_connections=1,
                keepalive_expiry=max(30, cls.retry_delay + 5),
            ),
            trust_env=False,
            # verify=True builds the TLS context on demand: httpcore mutates the passed-in
            # context in place (unlocked), so a shared singleton would race on concurrent handshakes.
            verify=True,
        )

    @classmethod
    async def _async_request(
        cls, client: httpx.AsyncClient, method: str, endpoint: str, **kwargs
    ) -> Dict:
        """Execute a single request on the given client; release back to the connection pool immediately after reading the response."""
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
                raise Exception(f"API returned an error: {result.get('msg', 'Unknown error')}")
            return result.get("data")
        finally:
            if response is not None:
                try:
                    await response.aclose()
                except Exception:
                    # Constraint: release errors must be swallowed so they do not mask business exceptions or break retry logic
                    pass

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """Determine if exception should be retried"""
        # Network-related errors
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # RemoteProtocolError: only retry the "without sending a response" variant (request not
        # sent, safe). Truncated variants may have been processed already; do not retry.
        if isinstance(exception, httpx.RemoteProtocolError):
            return "without sending a response" in str(exception)

        # HTTP status code error
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    async def _retry_wait(cls):
        """Retry wait interruptible by safe_close() (polls _closed every _RETRY_WAIT_SLICE seconds).

        Constraint: never sleep the full retry_delay in one shot, otherwise shutdown would
        wait out the entire retry cycle.
        """
        remaining = cls.retry_delay
        while remaining > 0 and not cls._closed:
            step = min(_RETRY_WAIT_SLICE, remaining)
            await asyncio.sleep(step)
            remaining -= step

    @classmethod
    async def _execute_async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """Business request executor with a retry mechanism.

        Constraint: the client is built once for the whole retry sequence and closed via
        ``async with``; safe_close does not cancel an in-flight attempt, it only interrupts
        the retry wait (raising ManageApiShutdownError).
        """
        client = cls._build_client()
        async with client:
            retry_count = 0

            while retry_count <= cls.max_retries:
                try:
                    # Execute asynchronous request
                    return await cls._async_request(client, method, endpoint, **kwargs)
                except Exception as e:
                    # Determine if retry is needed
                    if retry_count < cls.max_retries and cls._should_retry(e):
                        retry_count += 1
                        print(
                            f"{method} {endpoint} async request failed. Retrying in {cls.retry_delay:.1f}s (attempt {retry_count})"
                        )
                        await cls._retry_wait()
                        if cls._closed:
                            # The terminal state must stay distinguishable: a bare raise would disguise the
                            # shutdown early-exit as network jitter and mask the offline signal
                            raise ManageApiShutdownError(
                                f"safe_close interrupted the retry wait: {e}") from e
                        continue
                    else:
                        # Do not retry, Throw exception directly
                        raise

    @classmethod
    def _get_instance(cls) -> Optional["ManageApiClient"]:
        """Thread-safely obtain a reference to the singleton instance.

        Constraint: callers keep the returned local reference; never re-read _instance after a null check (TOCTOU window).
        """
        with cls._instance_lock:
            return cls._instance

    @classmethod
    def safe_close(cls):
        """Close entry point; in-flight requests release their clients inside their own event loops.

        Already-started requests are not cancelled; pending retry waits are interrupted,
        skipping the remaining retries (see _retry_wait).
        """
        with cls._instance_lock:
            cls._closed = True
            cls._instance = None


def api_guard(error_msg: str = None, raise_when_closed: bool = False):
    """Decorator: uniform singleton lookup, null check and exception fallback.

    - Fetches the instance once via _get_instance() and injects it as the decorated
      function's first parameter, eliminating the TOCTOU race against safe_close();
    - If the instance is uninitialized or closed: raise an explicit exception when
      raise_when_closed=True (startup paths), otherwise return None silently (daemon threads);
    - When error_msg is set, request exceptions are caught, logged and None is returned;
      when it is None, exceptions propagate to the caller.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            instance = ManageApiClient._get_instance()
            if instance is None:
                if raise_when_closed:
                    raise Exception("ManageApiClient is uninitialized or closed")
                return None
            if error_msg is None:
                return await func(instance, *args, **kwargs)
            try:
                return await func(instance, *args, **kwargs)
            except Exception as e:
                # Constraint: log the full stack trace for httpx/ValueError parsing failures (the
                # message alone hides context); keep other paths to a one-line log
                if isinstance(e, (httpx.HTTPError, ValueError)):
                    print(f"{error_msg}: {e}\n{traceback.format_exc()}")
                else:
                    print(f"{error_msg}: {e}")
                return None

        return wrapper

    return decorator


@api_guard(raise_when_closed=True)
async def get_server_config(instance) -> Optional[Dict]:
    """Get server base configuration"""
    return await instance._execute_async_request("POST", "/config/server-base")


@api_guard(raise_when_closed=True)
async def get_agent_models(
    instance, mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """Get agent model configuration"""
    return await instance._execute_async_request(
        "POST",
        "/config/agent-models",
        json={
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module,
        },
    )


@api_guard("Failed to get replacement words")
async def get_correct_words(instance, mac_address: str) -> Optional[Dict]:
    """Get agent replacement words"""
    return await instance._execute_async_request(
        "POST", "/config/correct-words",
        json={"macAddress": mac_address}
    )


@api_guard("Failed to generate and save chat summary")
async def generate_and_save_chat_summary(instance, session_id: str) -> Optional[Dict]:
    """Generate and save chat summary (daemon thread; returns None silently when the service is closing)."""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-summary/{session_id}/save",
    )


@api_guard("Failed to generate and save chat title")
async def generate_and_save_chat_title(instance, session_id: str) -> Optional[Dict]:
    """Generate and save chat title (daemon thread; returns None silently when the service is closing)."""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-title/{session_id}/generate",
    )


@api_guard("TTS report failed")
async def report(
    instance, mac_address: str, session_id: str, chat_type: int, content: str, audio, report_time
) -> Optional[Dict]:
    """Report chat history asynchronously"""
    if not content:
        return None
    return await instance._execute_async_request(
        "POST",
        "/agent/chat-history/report",
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


@api_guard("Contact lookup failed")
async def lookup_address_book(instance, caller_mac: str, nickname: str) -> Optional[Dict]:
    """Look up the target device by nickname"""
    return await instance._execute_async_request(
        "GET",
        f"/device/address-book/lookup?callerMac={caller_mac}&nickname={nickname}",
    )


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
