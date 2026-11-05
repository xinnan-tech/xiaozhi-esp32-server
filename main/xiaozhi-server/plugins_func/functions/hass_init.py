from config.logger import setup_logging
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


def _devices_text(devices) -> str:
    """把 devices 配置转成拼进提示词的文字。

    config.yaml 示例和手机端智控台给的是列表，每项一条"位置,设备名,entity_id"，这里拼成每行一条；
    网页端智控台和 HA 集成文档是一段字符串，原样用；其它（如 None）当空。
    """
    if isinstance(devices, (list, tuple)):
        return "\n".join(str(d).strip() for d in devices if str(d).strip())
    return devices if isinstance(devices, str) else ""


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
            else "hass_state"
        )

        if "hass_get_state" in funcs or "hass_set_state" in funcs:
            prompt = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
            deviceStr = _devices_text(
                plugins_config.get(config_source, {}).get("devices", "")
            )
            conn.prompt += prompt + deviceStr + "\n"
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
        "home_assistant" if plugins_config.get("home_assistant") else "hass_state"
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
