"""Device calling tool"""
import httpx
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

call_device_function_desc = {
    "type": "function",
    "function": {
        "name": "call_device",
        "description": (
            "Establish a voice call connection between devices. "
            "Call this tool when the user expresses one of these intents:\n"
            "1. Outgoing call: call it when the user says things like "
            "\"call XX / phone XX / connect me to XX / dial XX / get me XX on the line\"; "
            "take XX as the nickname. "
            "Examples: \"call John\" -> nickname=\"John\", "
            "\"connect me to Sarah\" -> nickname=\"Sarah\";\n"
            "2. Answering an incoming call: right after the system announces "
            "\"Incoming call from XX, do you want to answer?\", call it when the "
            "user says \"answer / pick up / yes answer / yes connect / yes talk\"; "
            "take XX from the announcement as the nickname.\n"
            "If the user's input is neither a clear acceptance nor a clear refusal, "
            "do NOT call call_device; you must ask once first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nickname": {"type": "string", "description": "Display name of the target device, e.g. John, Sarah"},
            },
            "required": ["nickname"],
        },
    },
}


async def _request_api(url: str, params: dict, headers: dict):
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        return await client.get(url, params=params, headers=headers)


def _failed_reply(msg: str) -> ActionResponse:
    return ActionResponse(action=Action.RESPONSE, response=msg)


def _is_answering(conn: "ConnectionHandler") -> bool:
    """Whether this is answer mode (conn.incoming_call is not empty)"""
    return hasattr(conn, 'incoming_call') and conn.incoming_call is not None


@register_function("call_device", call_device_function_desc, ToolType.SYSTEM_CTL)
async def call_device(conn: "ConnectionHandler", nickname: str):
    caller_mac = conn.headers.get("device-id")
    if not caller_mac:
        return _failed_reply("Unable to get this device's MAC address")

    api_config = conn.config.get("manager-api", {})
    api_url = api_config.get("url")
    api_secret = api_config.get("secret")
    if not api_url or not api_secret:
        logger.bind(tag=TAG).error("manager-api configuration missing")
        return _failed_reply("Configuration error, please try again later")

    headers = {"Authorization": f"Bearer {api_secret}"}

    # Distinguish outgoing call from answering an incoming call
    is_answer = _is_answering(conn)
    params = {"callerMac": caller_mac, "nickname": nickname}
    if is_answer:
        params["answer"] = "true"

    # Look up the address book and place the call
    try:
        resp = await _request_api(
            f"{api_url}/device/address-book/call",
            params=params,
            headers=headers,
        )
        result = resp.json()
    except httpx.HTTPError as e:
        logger.bind(tag=TAG).error(f"Call request failed: {e}")
        return _failed_reply("Call failed, please try again later")

    if result.get("code") != 0:
        return _failed_reply(result.get("msg", "Call failed"))

    data = result.get("data", {})
    if data.get("status") == "error":
        return _failed_reply(data.get("message"))

    if is_answer:
        return ActionResponse(action=Action.NONE, response="Call answered")
    else:
        conn.calling = True
        return ActionResponse(action=Action.NONE, response=f"Calling {nickname}, please wait for them to answer")
