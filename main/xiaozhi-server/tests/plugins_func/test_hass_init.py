"""append_devices_to_prompt：devices 写成列表或一段字符串都能拼进提示词。

config.yaml 示例和手机端智控台给的是列表，以前会报
can only concatenate str (not "list") to str，设备清单进不了提示词，模型只能猜 entity_id。
"""
import pytest

import plugins_func.functions.hass_state  # noqa: F401  注册 hass_state 模块，填充 module_func_map
from plugins_func.functions.hass_init import append_devices_to_prompt

HEADER = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
BASE_PROMPT = "你是小智。"


class FakeDialogue:
    def __init__(self):
        self.system_messages = []

    def update_system_message(self, prompt):
        self.system_messages.append(prompt)


class FakeConn:
    def __init__(self, plugin, source="home_assistant", functions=("hass_get_state", "hass_set_state")):
        self.intent_type = "function_call"
        self.config = {
            "selected_module": {"Intent": "function_call"},
            "Intent": {"function_call": {"functions": list(functions)}},
            "plugins": {source: plugin},
        }
        self.prompt = BASE_PROMPT
        self.dialogue = FakeDialogue()


def _plugin(**extra):
    return {"base_url": "http://homeassistant.local:8123", "api_key": "test-token", **extra}


def test_list_devices_one_per_line():
    conn = FakeConn(_plugin(devices=[
        "客厅,玩具灯,switch.toy_lamp",
        " 卧室,台灯,switch.desk_lamp ",
        "",
    ]))
    append_devices_to_prompt(conn)
    expected = BASE_PROMPT + HEADER + "客厅,玩具灯,switch.toy_lamp\n卧室,台灯,switch.desk_lamp\n"
    assert conn.prompt == expected
    assert conn.dialogue.system_messages == [expected]


def test_string_devices_kept_as_is():
    # 网页端智控台和 HA 集成文档给的是一段字符串
    devices = "客厅,玩具灯,switch.toy_lamp;\n卧室,台灯,switch.desk_lamp;"
    conn = FakeConn(_plugin(devices=devices))
    append_devices_to_prompt(conn)
    assert conn.prompt == BASE_PROMPT + HEADER + devices + "\n"


def test_mobile_console_hass_state_list():
    # 智控台下发的插件配置键是 hass_state；手机端把 array 字段按行切成了列表
    conn = FakeConn(_plugin(devices=["客厅,玩具灯,switch.toy_lamp"]), source="hass_state")
    append_devices_to_prompt(conn)
    assert conn.prompt.endswith(HEADER + "客厅,玩具灯,switch.toy_lamp\n")


def test_module_name_in_functions():
    # functions 里写模块名 hass_state（config.yaml 注释的写法），展开后应能匹配
    conn = FakeConn(_plugin(devices=["客厅,玩具灯,switch.toy_lamp"]), functions=("hass_state",))
    append_devices_to_prompt(conn)
    assert conn.prompt.endswith(HEADER + "客厅,玩具灯,switch.toy_lamp\n")


@pytest.mark.parametrize("plugin", [_plugin(), _plugin(devices=None), _plugin(devices=[])])
def test_missing_or_empty_devices_does_not_raise(plugin):
    conn = FakeConn(plugin)
    append_devices_to_prompt(conn)
    assert conn.prompt == BASE_PROMPT + HEADER + "\n"


def test_without_hass_functions_prompt_unchanged():
    conn = FakeConn(_plugin(devices=["客厅,玩具灯,switch.toy_lamp"]), functions=("get_weather",))
    append_devices_to_prompt(conn)
    assert conn.prompt == BASE_PROMPT
    assert conn.dialogue.system_messages == []
