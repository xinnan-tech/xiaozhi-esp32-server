from config.logger import setup_logging
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


def append_devices_to_prompt(conn):
    if conn.intent_type == "function_call":
        funcs = conn.config["Intent"][conn.config["selected_module"]["Intent"]].get(
            "functions", []
        )

        # 安全地获取插件配置
        plugins_config = conn.config.get("plugins", {})
        config_source = (
            "home_assistant"
            if plugins_config.get("home_assistant")
            else "hass_get_state"
        )

        if "hass_get_state" in funcs or "hass_set_state" in funcs:
            devices = plugins_config.get(config_source, {}).get("devices", "")
            
            # 格式化设备清单
            if isinstance(devices, list):
                device_lines = []
                for d in devices:
                    parts = d.split(",")
                    if len(parts) == 3:
                        location, name, entity_id = parts
                        device_lines.append(f"- {name} (位置:{location}): {entity_id}")
                    else:
                        device_lines.append(f"- {d}")
                device_str = "\n".join(device_lines)
            else:
                device_str = str(devices)
            
            # 构建提示词
            prompt = (
                "\n<function_call_context>\n"
                "[Home Assistant智能设备清单]\n"
                "当你需要控制Home Assistant设备时,必须使用下面列出的确切entity_id,不能自己编造!\n"
                f"{device_str}\n"
                "</function_call_context>\n"
            )
            
            conn.prompt += prompt
            # 更新提示词
            conn.dialogue.update_system_message(conn.prompt)


def initialize_hass_handler(conn):
    ha_config = {}
    if not conn.load_function_plugin:
        return ha_config

    # 安全地获取插件配置
    plugins_config = conn.config.get("plugins", {})
    # 确定配置来源
    config_source = (
        "home_assistant" if plugins_config.get("home_assistant") else "hass_get_state"
    )
    if not plugins_config.get(config_source):
        return ha_config

    # 统一获取配置
    plugin_config = plugins_config[config_source]
    ha_config["base_url"] = plugin_config.get("base_url")
    ha_config["api_key"] = plugin_config.get("api_key")

    # 统一检查API密钥
    model_key_msg = check_model_key("home_assistant", ha_config.get("api_key"))
    if model_key_msg:
        logger.bind(tag=TAG).error(model_key_msg)

    return ha_config
