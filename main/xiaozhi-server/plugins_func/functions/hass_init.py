from config.logger import setup_logging
from core.utils.util import check_model_key
from plugins_func.register import module_func_map

TAG = __name__
logger = setup_logging()


def _expand_module_names(funcs):
    """把 functions 列表里的模块名（如 hass_state）展开成具体函数名，与工具加载口径一致。"""
    expanded = []
    for name in funcs:
        expanded.extend(module_func_map.get(name, [name]))
    return expanded


def _devices_text(devices) -> str:
    """把 devices 配置转成拼进提示词的文字。

    config.yaml 示例和手机端智控台给的是列表，每项一条"位置,设备名,entity_id"，这里拼成每行一条；
    网页端智控台和 HA 集成文档是一段字符串，原样用；其它（如 None）当空。
    """
    if isinstance(devices, (list, tuple)):
        return "\n".join(
            str(d).strip() for d in devices if d is not None and str(d).strip()
        )
    return devices if isinstance(devices, str) else ""


def _hass_plugin_config(plugins_config: dict) -> dict:
    """取 HA 插件配置：优先本地 config.yaml 的 home_assistant，其次智控台下发的 hass_state。"""
    for key in ("home_assistant", "hass_state"):
        cfg = plugins_config.get(key)
        if cfg:
            return cfg
    return {}


def append_devices_to_prompt(conn):
    if conn.intent_type == "function_call":
        funcs = _expand_module_names(
            conn.config["Intent"][conn.config["selected_module"]["Intent"]].get(
                "functions", []
            )
        )

        if "hass_get_state" in funcs or "hass_set_state" in funcs:
            prompt = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
            plugin_config = _hass_plugin_config(conn.config.get("plugins", {}))
            deviceStr = _devices_text(plugin_config.get("devices", ""))
            conn.prompt += prompt + deviceStr + "\n"
            # 更新提示词
            conn.dialogue.update_system_message(conn.prompt)


def initialize_hass_handler(conn):
    ha_config = {}
    if not conn.load_function_plugin:
        return ha_config

    plugin_config = _hass_plugin_config(conn.config.get("plugins", {}))
    if not plugin_config:
        return ha_config

    ha_config["base_url"] = plugin_config.get("base_url")
    ha_config["api_key"] = plugin_config.get("api_key")

    # 统一检查API密钥
    model_key_msg = check_model_key("home_assistant", ha_config.get("api_key"))
    if model_key_msg:
        logger.bind(tag=TAG).error(model_key_msg)

    return ha_config
