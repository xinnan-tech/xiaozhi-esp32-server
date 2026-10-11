import httpx
from config.logger import setup_logging
from plugins_func.functions.hass_init import initialize_hass_handler
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

hass_get_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_get_state",
        "description": "Get device state in homeassistant, including light brightness, color, color temperature, media player volume, and device pause/resume state",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Device id to query, entity_id in homeassistant",
                }
            },
            "required": ["entity_id"],
        },
    },
}

hass_set_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_set_state",
        "description": "Set device status in homeassistant, including on/off, adjust light brightness/color/color temperature, adjust player volume, device pause/resume/mute operations",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Action to perform, turn on device: turn_on, turn off device: turn_off, increase brightness: brightness_up, decrease brightness: brightness_down, set brightness: brightness_value, increase volume: volume_up, decrease volume: volume_down, set volume: volume_set, set color temperature: set_kelvin, set color: set_color, device pause: pause, device continue: continue, mute/unmute: volume_mute",
                        },
                        "input": {
                            "type": "integer",
                            "description": "Only needed when setting volume or brightness, valid values 1-100, corresponding to 1%-100% of volume and brightness",
                        },
                        "is_muted": {
                            "type": "string",
                            "description": "Only needed when setting mute operation, value is true when setting mute, false when unmuting",
                        },
                        "rgb_color": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Only needed when setting color, fill in the RGB value of the target color here",
                        },
                    },
                    "required": ["type"],
                },
                "entity_id": {
                    "type": "string",
                    "description": "Device id to operate, entity_id in homeassistant",
                },
            },
            "required": ["state", "entity_id"],
        },
    },
}


@register_function("hass_get_state", hass_get_state_function_desc, ToolType.SYSTEM_CTL)
async def hass_get_state(conn: "ConnectionHandler", entity_id=""):
    try:
        ha_response = await handle_hass_get_state(conn, entity_id)
        return ActionResponse(Action.REQLLM, ha_response, None)
    except httpx.TimeoutException:
        logger.bind(tag=TAG).error("获取Home Assistant状态超时")
        return ActionResponse(Action.ERROR, "请求超时", None)
    except Exception as e:
        error_msg = f"执行Home Assistant操作失败"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, error_msg, None)


@register_function("hass_set_state", hass_set_state_function_desc, ToolType.SYSTEM_CTL)
async def hass_set_state(conn: "ConnectionHandler", entity_id="", state=None):
    if state is None:
        state = {}
    try:
        ha_response = await handle_hass_set_state(conn, entity_id, state)
        return ActionResponse(Action.REQLLM, ha_response, None)
    except asyncio.TimeoutError:
        logger.bind(tag=TAG).error("Set Home Assistant status timeout")
        return ActionResponse(Action.ERROR, "Request timeout", None)
    except Exception as e:
        error_msg = f"Failed to execute Home Assistant operation"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, error_msg, None)


async def handle_hass_get_state(conn: "ConnectionHandler", entity_id):
    ha_config = initialize_hass_handler(conn)
    api_key = ha_config.get("api_key")
    base_url = ha_config.get("base_url")
    url = f"{base_url}/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 200:
        responsetext = "设备状态:" + response.json()["state"] + " "
        logger.bind(tag=TAG).info(f"api返回内容: {response.json()}")

        if "media_title" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "正在播放的是:"
                + str(response.json()["attributes"]["media_title"])
                + " "
            )
        if "volume_level" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "音量是:"
                + str(response.json()["attributes"]["volume_level"])
                + " "
            )
        if "color_temp_kelvin" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "色温是:"
                + str(response.json()["attributes"]["color_temp_kelvin"])
                + " "
            )
        if "rgb_color" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "rgb颜色是:"
                + str(response.json()["attributes"]["rgb_color"])
                + " "
            )
        if "brightness" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "亮度是:"
                + str(response.json()["attributes"]["brightness"])
                + " "
            )
        logger.bind(tag=TAG).info(f"查询返回内容: {responsetext}")
        return responsetext
    else:
        return f"切换失败，错误码: {response.status_code}"


async def handle_hass_set_state(conn: "ConnectionHandler", entity_id, state):
    ha_config = initialize_hass_handler(conn)
    api_key = ha_config.get("api_key")
    base_url = ha_config.get("base_url")
    """
    state = { "type":"brightness_up","input":"80","is_muted":"true"}
    """
    domains = entity_id.split(".")
    if len(domains) > 1:
        domain = domains[0]
    else:
        return "Execution failed, incorrect device id"
    action = ""
    arg = ""
    value = ""
    if state["type"] == "turn_on":
        description = "Device turned on"
        if domain == "cover":
            action = "open_cover"
        elif domain == "vacuum":
            action = "start"
        else:
            action = "turn_on"
    elif state["type"] == "turn_off":
        description = "Device turned off"
        if domain == "cover":
            action = "close_cover"
        elif domain == "vacuum":
            action = "stop"
        else:
            action = "turn_off"
    elif state["type"] == "brightness_up":
        description = "Light brightened"
        action = "turn_on"
        arg = "brightness_step_pct"
        value = 10
    elif state["type"] == "brightness_down":
        description = "Light dimmed"
        action = "turn_on"
        arg = "brightness_step_pct"
        value = -10
    elif state["type"] == "brightness_value":
        description = f"Brightness adjusted to {state['input']}"
        action = "turn_on"
        arg = "brightness_pct"
        value = state["input"]
    elif state["type"] == "set_color":
        description = f"Color adjusted to {state['rgb_color']}"
        action = "turn_on"
        arg = "rgb_color"
        value = state["rgb_color"]
    elif state["type"] == "set_kelvin":
        description = f"Color temperature adjusted to {state['input']}K"
        action = "turn_on"
        arg = "kelvin"
        value = state["input"]
    elif state["type"] == "volume_up":
        description = "Volume increased"
        action = state["type"]
    elif state["type"] == "volume_down":
        description = "Volume decreased"
        action = state["type"]
    elif state["type"] == "volume_set":
        description = f"Volume adjusted to {state['input']}"
        action = state["type"]
        arg = "volume_level"
        value = state["input"]
        if state["input"] >= 1:
            value = state["input"] / 100
    elif state["type"] == "volume_mute":
        description = f"Device muted"
        action = state["type"]
        arg = "is_volume_muted"
        value = state["is_muted"]
    elif state["type"] == "pause":
        description = f"Device paused"
        action = state["type"]
        if domain == "media_player":
            action = "media_pause"
        if domain == "cover":
            action = "stop_cover"
        if domain == "vacuum":
            action = "pause"
    elif state["type"] == "continue":
        description = f"Device resumed"
        if domain == "media_player":
            action = "media_play"
        if domain == "vacuum":
            action = "start"
    else:
        return f"{domain} {state['type']} function not yet supported"

    if arg == "":
        data = {
            "entity_id": entity_id,
        }
    else:
        data = {"entity_id": entity_id, arg: value}
    url = f"{base_url}/api/services/{domain}/{action}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=data, timeout=5)  # Set 5 second timeout
    logger.bind(tag=TAG).info(
        f"Set status: {description}, url: {url}, return_code: {response.status_code}"
    )
    if response.status_code == 200:
        return description
    else:
        return f"Set failed, error code: {response.status_code}"
