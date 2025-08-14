from plugins_func.register import register_function, ToolType, ActionResponse, Action
from plugins_func.functions.hass_init import initialize_hass_handler
from config.logger import setup_logging
import asyncio
import requests

TAG = __name__
logger = setup_logging()

hass_set_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_set_state",
        "description": "Set device status in homeassistant, including on/off, adjusting light brightness, color, color temperature, adjusting player volume, device pause/resume/mute operations",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Action to perform, turn on device: turn_on, turn off device: turn_off, increase brightness: brightness_up, decrease brightness: brightness_down, set brightness: brightness_value, increase volume: volume_up, decrease volume: volume_down, set volume: volume_set, set color temperature: set_kelvin, set color: set_color, device pause: pause, device resume: continue, mute/unmute: volume_mute",
                        },
                        "input": {
                            "type": "integer",
                            "description": "Only needed when setting volume or brightness, valid values 1-100, corresponding to 1%-100% volume and brightness",
                        },
                        "is_muted": {
                            "type": "string",
                            "description": "Only needed for mute operations, set to true when muting, false when unmuting",
                        },
                        "rgb_color": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Only needed when setting color, fill target color RGB values here",
                        },
                    },
                    "required": ["type"],
                },
                "entity_id": {
                    "type": "string",
                    "description": "Device ID to operate, entity_id in homeassistant",
                },
            },
            "required": ["state", "entity_id"],
        },
    },
}

@register_function("hass_set_state", hass_set_state_function_desc, ToolType.SYSTEM_CTL)
def hass_set_state(conn, entity_id="", state={}):
    try:
        future = asyncio.run_coroutine_threadsafe(
            handle_hass_set_state(conn, entity_id, state), conn.loop
        )
        ha_response = future.result()
        return ActionResponse(Action.REQLLM, ha_response, None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error processing set attribute intent: {e}")

async def handle_hass_set_state(conn, entity_id, state):
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
        return "Execution failed, invalid device id"
    
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
        description = "Light brightness increased"
        action = "turn_on"
        arg = "brightness_step_pct"
        value = 10
    
    elif state["type"] == "brightness_down":
        description = "Light brightness decreased"
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
        return f"{domain} {state.type} function not yet supported"
    
    if arg == "":
        data = {
            "entity_id": entity_id,
        }
    else:
        data = {"entity_id": entity_id, arg: value}
    
    url = f"{base_url}/api/services/{domain}/{action}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=data)
    
    logger.bind(tag=TAG).info(
        f"Set status: {description}, url: {url}, return_code: {response.status_code}"
    )
    
    if response.status_code == 200:
        return description
    else:
        return f"Setting failed, error code: {response.status_code}"