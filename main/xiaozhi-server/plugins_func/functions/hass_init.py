from config.logger import setup_logging
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()

HASS_CACHE = {}


def append_devices_to_prompt(conn):
    if conn.use_function_call_mode:
        funcs = conn.config["Intent"][conn.config["selected_module"]["Intent"]].get(
            "functions", []
        )
        if "hass_get_state" in funcs or "hass_set_state" in funcs:
            prompt = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
            devices = conn.config["plugins"]["home_assistant"].get("devices", [])
            if len(devices) == 0:
                return
            for device in devices:
                prompt += device + "\n"
            conn.prompt += prompt
            # 更新提示词
            conn.dialogue.update_system_message(conn.prompt)


def initialize_hass_handler(conn):
    global HASS_CACHE
    if HASS_CACHE == {}:
        if conn.use_function_call_mode:
            funcs = conn.config["Intent"][conn.config["selected_module"]["Intent"]].get(
                "functions", []
            )
            if "hass_get_state" in funcs or "hass_set_state" in funcs:
                HASS_CACHE["base_url"] = conn.config["plugins"]["home_assistant"].get(
                    "base_url"
                )
                HASS_CACHE["api_key"] = conn.config["plugins"]["home_assistant"].get(
                    "api_key"
                )

                check_model_key("home_assistant", HASS_CACHE["api_key"])
    return HASS_CACHE
