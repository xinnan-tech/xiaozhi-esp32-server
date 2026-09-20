import sys
import traceback
import asyncio

# 简单的logger实现，用于测试
class SimpleLogger:
    def __init__(self):
        self.tag = ''  # 初始化tag属性

    def bind(self, **kwargs):
        self.tag = kwargs.get('tag', '')
        return self

    def info(self, message):
        print(f"[INFO] [{self.tag}] {message}")

    def debug(self, message):
        print(f"[DEBUG] [{self.tag}] {message}")

    def error(self, message):
        print(f"[ERROR] [{self.tag}] {message}")

    def warning(self, message):
        print(f"[WARNING] [{self.tag}] {message}")

# 简单的conn模拟
class MockConn:
    def __init__(self):
        self.logger = SimpleLogger()

try:
    # 尝试导入插件模块
    from plugins.preprocess_plugin import PreprocessPlugin
    print("插件导入成功")

    # 创建logger实例
    logger = SimpleLogger()

    # 尝试创建插件实例，传入logger
    plugin = PreprocessPlugin(logger=logger)
    print("插件实例化成功")

    # 测试插件的pre_process_text方法
    async def test_preprocess():
        mock_conn = MockConn()
        # 测试多个智能家居指令
        test_commands = [
            # 开关指令测试
            "将卧室灯带亮度调整为50",
            "打开客厅灯",
            "打开客厅吊灯",
            "打开所有灯",
            "打开所有吊灯",
            "打开所有筒灯",
            "打开客厅筒灯",
            "打开筒灯",
            "打开餐厅吊灯",
            "打开餐桌吊灯",
            "开灯",
            "关灯",
            # 悬浮灯带测试
            "打开悬浮灯带",
            "关闭悬浮灯带",
            "将悬浮灯带亮度调整为50",
            "亮度调整为80",  # 不指定设备，测试默认设备匹配
            "卧室亮度调整为60",  # 指定区域，测试区域匹配
            # 其他亮度命令测试
            "将亮度调整为90",
            "客厅亮度调整为70",
            # 灯带测试
            "打开灯带",
            "关闭灯带",
            # 特殊命令测试
            "打印设备列表",
            # 复杂命令测试（放行给LLM）
            "今天天气怎么样",
            "帮我播放音乐",
            "明天几点起床合适"
        ]

        # 模拟设备列表，绕过API调用
        original_fetch_entities = plugin._fetch_entities
        async def mock_fetch_entities(conn):
            entities = [
                {
                    "names": "入户门",
                    "state": "off",
                    "areas": "玄关",
                    "attributes": None,
                    "device_class": "door"
                },
                {
                    "names": "厨房筒灯",
                    "state": "off",
                    "areas": "厨房",
                    "attributes": None,
                    "device_class": "switch"
                },
                {
                    "names": "右筒灯",
                    "state": "off",
                    "areas": "客厅",
                    "attributes": None,
                    "device_class": "switch"
                },
                {
                    "names": "客厅吊灯",
                    "state": "on",
                    "areas": "客厅",
                    "attributes": None,
                    "device_class": "switch"
                },
                {
                    "names": "左筒灯",
                    "state": "off",
                    "areas": "客厅",
                    "attributes": None,
                    "device_class": "switch"
                },
                {
                    "names": "悬浮灯带",
                    "state": "off",
                    "areas": "卧室",
                    "attributes": None,
                    "brightness": None,
                    "device_class": "light"
                },
                {
                    "names": "温度",
                    "state": 19.5,
                    "areas": "客厅",
                    "attributes": None,
                    "unit_of_measurement": "°C",
                    "device_class": "temperature"
                },
                {
                    "names": "湿度",
                    "state": 59,
                    "areas": "客厅",
                    "attributes": None,
                    "unit_of_measurement": "'",
                    "device_class": "humidity"
                },
                {
                    "names": "餐桌吊灯",
                    "state": "off",
                    "areas": "餐厅",
                    "attributes": None,
                    "device_class": "switch"
                }
            ]

            return entities

        # 替换_fetch_entities方法
        plugin._fetch_entities = mock_fetch_entities

        # 手动初始化设备列表、区域和子串字典（模拟异步初始化）
        entities = await mock_fetch_entities(None)
        plugin.device_list_cache = entities
        plugin.device_list_initialized = True

        # 提取所有区域
        plugin.device_areas = {d.get("areas", "") for d in entities if d.get("areas")}

        # 生成设备子串字典
        all_names = {d.get("names", "") for d in entities if d.get("names")}
        substrings = set()
        for name in all_names:
            length = len(name)
            for i in range(length):
                for j in range(i + 1, length + 1):
                    substrings.add(name[i:j])
        plugin.device_substrings = sorted(list(substrings), key=len, reverse=True)

        # 动态注册 area 和 deviceName slot
        if plugin.device_areas:
            plugin.template_matcher.register_dynamic_slot(
                "area",
                list(plugin.device_areas),
                is_optional=False
            )
        if plugin.device_substrings:
            plugin.template_matcher.register_dynamic_slot(
                "deviceName",
                plugin.device_substrings,
                is_optional=False
            )

        print(f"设备初始化完成：{len(entities)} 个设备，{len(plugin.device_areas)} 个区域，{len(plugin.device_substrings)} 个子串")
        print("\\n=== 开始测试智能家居指令预处理 ===")
        for command in test_commands:
            print(f"\\n测试命令: {command}")
            try:
                result, action = await plugin.pre_process_text(mock_conn, command)
                print(f"预处理结果: {result}")
                print(f"返回动作: {action}")
            except Exception as e:
                print(f"处理出错: {e}")
        print("\\n=== 测试结束 ===")

        # 恢复原始方法
        plugin._fetch_entities = original_fetch_entities

    # 运行异步测试
    asyncio.run(test_preprocess())

    print("插件测试通过")

    # ========== 新增单元测试 ==========
    print("\\n\\n=== 开始新增单元测试 ===")
    from plugins.preprocess_plugin import PreprocessPlugin, TemplateMatcher

    # 测试1: TemplateMatcher - 严格顺序匹配
    print("\\n测试1: TemplateMatcher - 严格顺序匹配")
    config1 = {
        "action_mapping": {"turn_on": ["打开", "开启", "开", "启动"]},
        "operation_templates": {
            "turn_on": ["{action_word} {deviceName}", "{action_word} {area} {deviceName}"]
        },
        "slots_config": {
            "request_word": ["请", "帮我", "给我", "我要"],
            "all_word": ["全部", "所有", "都"]
        }
    }
    matcher1 = TemplateMatcher(config1)
    # 需要手动注册 deviceName slot 用于测试
    matcher1.register_dynamic_slot("deviceName", ["筒灯", "吊灯", "客厅吊灯", "左筒灯", "右筒灯"], is_optional=False)

    # 测试1a: 简单匹配
    result1a = matcher1.match_template("{action_word} {deviceName}", "打开筒灯")
    assert result1a is not None, "应该匹配"
    assert result1a["action"] == "turn_on", f"期望turn_on，实际{result1a['action']}"
    assert result1a["device_name"] == "筒灯", f"期望筒灯，实际{result1a['device_name']}"
    print("  [PASS] 简单匹配测试通过")

    # 测试1b: 剩余字符验证（带感叹号应失败）
    result1b = matcher1.match_template("{action_word} {deviceName}", "打开筒灯！")
    assert result1b is None, "带感叹号应匹配失败"
    print("  [PASS] 剩余字符验证测试通过")

    # 测试1c: 顺序匹配（先action后deviceName）
    result1c = matcher1.match_template("{action_word} {deviceName}", "打开客厅吊灯")
    assert result1c is not None, "应该匹配"
    assert result1c["device_name"] == "客厅吊灯", f"期望客厅吊灯，实际{result1c['device_name']}"
    print("  [PASS] 顺序匹配测试通过")

    # 测试2: 动态注册 area 和 deviceName
    print("\\n测试2: 动态注册和匹配")
    config2 = {
        "action_mapping": {"turn_on": ["打开"]},
        "operation_templates": {"turn_on": ["{action_word} {area} {deviceName}"]},
        "slots_config": {}
    }
    matcher2 = TemplateMatcher(config2)

    # 动态注册
    matcher2.register_dynamic_slot("area", ["客厅", "卧室"], is_optional=False)
    matcher2.register_dynamic_slot("deviceName", ["吊灯", "筒灯", "客厅吊灯"], is_optional=False)

    result2 = matcher2.match_template("{action_word} {area} {deviceName}", "打开客厅吊灯")
    assert result2 is not None, "应该匹配"
    assert result2["area"] == "客厅", f"期望客厅，实际{result2['area']}"
    assert result2["device_name"] == "吊灯", f"期望吊灯，实际{result2['device_name']}"
    print("  [PASS] 动态注册测试通过")

    # 测试3: 可选 slot（request_word）
    print("\\n测试3: 可选 slot 匹配")
    config3 = {
        "action_mapping": {"turn_on": ["打开"]},
        "operation_templates": {"turn_on": ["{request_word} {action_word} {deviceName}"]},
        "slots_config": {"request_word": ["请", "帮我"]}
    }
    matcher3 = TemplateMatcher(config3)
    matcher3.register_dynamic_slot("deviceName", ["筒灯"], is_optional=False)

    # 有 request_word - 应该匹配
    result3a = matcher3.match_template("{request_word} {action_word} {deviceName}", "请打开筒灯")
    assert result3a is not None, "有request_word应匹配"
    assert result3a["has_request_word"] == True, "应标记has_request_word"
    print("  [PASS] 有request_word匹配测试通过")

    # 无 request_word - 可选 slot 不匹配，继续下一个，最终匹配成功
    result3b = matcher3.match_template("{request_word} {action_word} {deviceName}", "打开筒灯")
    assert result3b is not None, "request_word可选，应匹配成功"
    assert result3b["has_request_word"] == False, "不应标记has_request_word"
    print("  [PASS] 无request_word匹配测试通过")

    # 测试可选性：使用另一个模板，不包含 request_word
    result3c = matcher3.match_template("{action_word} {deviceName}", "打开筒灯")
    assert result3c is not None, "不包含request_word的模板应匹配"
    assert result3c["has_request_word"] == False, "不应标记has_request_word"
    print("  [PASS] 可选 slot 测试通过")

    # 测试4: 区域过滤（使用现有方法）
    print("\\n测试4: 区域过滤")
    devices4 = [
        {"names": "客厅吊灯", "areas": "客厅", "device_class": "light"},
        {"names": "卧室灯", "areas": "卧室", "device_class": "light"}
    ]
    plugin4 = PreprocessPlugin()
    config4 = {"global": {"default_area": "客厅", "restrict_to_default_area": True}}
    plugin4.config = config4

    # 有指定区域
    result4a = plugin4._filter_by_area(devices4, "客厅", devices4)
    assert len(result4a) == 1, f"期望1个设备，实际{len(result4a)}"

    # 无指定区域，使用默认区域限制
    result4b = plugin4._filter_by_area(devices4, None, devices4)
    assert len(result4b) == 1, f"期望1个设备，实际{len(result4b)}"
    print("  [PASS] 区域过滤测试通过")

    # 测试5: 设备查找
    print("\\n测试5: 设备查找")
    devices5 = [
        {"names": "左筒灯", "areas": "客厅", "device_class": "light"},
        {"names": "右筒灯", "areas": "客厅", "device_class": "light"},
        {"names": "客厅吊灯", "areas": "客厅", "device_class": "light"}
    ]
    plugin5 = PreprocessPlugin()

    # 无区域查找
    result5a = plugin5._find_devices_by_name_and_area("筒灯", None, devices5)
    assert len(result5a) == 2, f"期望2个设备，实际{len(result5a)}"

    # 有区域查找
    result5b = plugin5._find_devices_by_name_and_area("筒灯", "客厅", devices5)
    assert len(result5b) == 2, f"期望2个设备，实际{len(result5b)}"
    print("  [PASS] 设备查找测试通过")

    # 测试6: 操作支持检查
    print("\\n测试6: 操作支持检查")
    devices6 = [
        {"names": "客厅吊灯", "areas": "客厅", "device_class": "light"},
        {"names": "客厅开关", "areas": "客厅", "device_class": "switch"},
        {"names": "温度传感器", "areas": "客厅", "device_class": "sensor"}
    ]
    plugin6 = PreprocessPlugin()
    result6 = plugin6._filter_supported_devices(devices6, "set_brightness")
    assert len(result6) == 1, f"期望1个设备（只有light支持set_brightness），实际{len(result6)}"
    assert result6[0]["names"] == "客厅吊灯", f"期望客厅吊灯，实际{result6[0]['names']}"
    print("  [PASS] 操作支持检查测试通过")

    # 测试7: 默认设备规则
    print("\\n测试7: 默认设备规则")
    devices7 = [
        {"names": "左筒灯", "areas": "客厅", "device_class": "light"},
        {"names": "右筒灯", "areas": "客厅", "device_class": "light"},
        {"names": "客厅吊灯", "areas": "客厅", "device_class": "light"}
    ]
    config7 = {"default_devices": ["客厅吊灯"]}
    plugin7 = PreprocessPlugin()
    plugin7.config = config7
    result7 = plugin7._apply_default_device_rule(devices7)
    assert len(result7) == 1, f"期望1个设备，实际{len(result7)}"
    assert result7[0]["names"] == "客厅吊灯", f"期望客厅吊灯，实际{result7[0]['names']}"
    print("  [PASS] 默认设备规则测试通过")

    print("\\n=== 所有单元测试通过！===\\n")

    # ========== 新增：自定义 slots 测试 ==========
    print("\\n=== 测试自定义 slots ===")

    # 测试 1: NUMBER 格式
    print("\\n测试1: NUMBER 格式")
    config = {
        "action_mapping": {"设置": ["设置"]},
        "operation_templates": {"设置": ["{action_word} {deviceName} {temperature_value}"]},
        "slots_config": {"temperature_value": "NUMBER"}
    }
    matcher = TemplateMatcher(config)
    matcher.register_dynamic_slot("deviceName", ["空调"], is_optional=False)
    result = matcher.match_template("{action_word} {deviceName} {temperature_value}", "设置空调26")
    assert result is not None and result["custom_slots"]["temperature_value"] == "26"
    print("  [PASS] NUMBER 格式测试通过")

    # 测试 2: 普通列表格式
    print("\\n测试2: 普通列表格式")
    config = {
        "action_mapping": {"切换": ["切换"]},
        "operation_templates": {"切换": ["{action_word} {deviceName} {mode_value}"]},
        "slots_config": {"mode_value": ["自动模式", "手动模式"]}
    }
    matcher = TemplateMatcher(config)
    matcher.register_dynamic_slot("deviceName", ["空调"], is_optional=False)
    result = matcher.match_template("{action_word} {deviceName} {mode_value}", "切换空调自动模式")
    assert result is not None and result["custom_slots"]["mode_value"] == "自动模式"
    print("  [PASS] 普通列表格式测试通过")

    # 测试 3: 多个自定义 slots
    print("\\n测试3: 多个自定义 slots")
    config = {
        "action_mapping": {"设置": ["设置"]},
        "operation_templates": {"设置": ["{action_word} {deviceName} {temperature_value} {speed_value}"]},
        "slots_config": {
            "temperature_value": "NUMBER",
            "speed_value": {"一档": 1, "二档": 2, "三档": 3}
        }
    }
    matcher = TemplateMatcher(config)
    matcher.register_dynamic_slot("deviceName", ["空调"], is_optional=False)
    result = matcher.match_template("{action_word} {deviceName} {temperature_value} {speed_value}", "设置空调26 二档")
    assert result is not None
    assert result["custom_slots"]["temperature_value"] == "26"
    assert result["custom_slots"]["speed_value"] == "二档"
    print("  [PASS] 多个自定义 slots 测试通过")

    # 测试 4: 可选 slots（通过模板回溯）
    print("\\n测试4: 可选 slots（模板回溯）")
    config = {
        "action_mapping": {"打开": ["打开"]},
        "operation_templates": {
            "打开": ["{request_word} {action_word} {deviceName}", "{action_word} {deviceName}"]
        },
        "slots_config": {"request_word": ["请", "帮我"]}
    }
    matcher = TemplateMatcher(config)
    matcher.register_dynamic_slot("deviceName", ["灯"], is_optional=False)

    # 带 request_word
    result1 = matcher.match_template("{request_word} {action_word} {deviceName}", "请打开灯")
    assert result1 is not None and result1["has_request_word"] == True

    # 不带 request_word（第二个模板）
    result2 = matcher.match_template("{action_word} {deviceName}", "打开灯")
    assert result2 is not None and result2["has_request_word"] == False
    print("  [PASS] 可选 slots 测试通过")

    print("\\n=== 所有自定义 slots 测试通过！===\\n")

    # ========== 新增：亮度控制命令测试 ==========
    print("\\n=== 测试亮度控制命令匹配 ===")

    # 测试命令: "将悬浮灯带亮度调整为50"
    print("\\n测试: 将悬浮灯带亮度调整为50")
    config_brightness = {
        "action_mapping": {"set_brightness": ["调亮", "调亮一点", "调亮些", "加亮", "调暗", "调暗一点", "调暗些", "减亮"]},
        "operation_templates": {
            "set_brightness": [
                "{request_word} {deviceName} {construct_word} {brightness_value}",
                "{request_word} {deviceName} {construct_word} {number_value}",
                "{request_word} {deviceName} {brightness_value}",
                "{request_word} {area} {deviceName} {brightness_value}",
                "{action_word} {deviceName} {number_value}%",
                "{request_word} {action_word} {deviceName} {number_value}%",
                "{deviceName} {number_value}%"
            ]
        },
        "slots_config": {
            "request_word": ["请", "帮我", "给我", "我要", "将", "把"],
            "construct_word": ["调整为", "设置为", "改为", "变成", "调整到", "调到", "设为", "亮度调整为", "亮度调整到", "亮度设为", "亮度改为", "亮度调到"],
            "brightness_value": {"最亮": 100, "最暗": 1, "高": 80, "中": 50, "低": 20},
            "number_value": "NUMBER"
        }
    }

    matcher_brightness = TemplateMatcher(config_brightness)
    matcher_brightness.register_dynamic_slot("deviceName", ["悬浮灯带", "客厅吊灯", "卧室灯"], is_optional=False)
    matcher_brightness.register_dynamic_slot("area", ["客厅", "卧室"], is_optional=False)

    # 测试1: "将悬浮灯带亮度调整为50"
    result_b1 = matcher_brightness.match_template("{request_word} {deviceName} {construct_word} {number_value}", "将悬浮灯带亮度调整为50")
    assert result_b1 is not None, "应该匹配"
    assert result_b1["device_name"] == "悬浮灯带", f"期望悬浮灯带，实际{result_b1.get('device_name')}"
    assert result_b1["custom_slots"]["number_value"] == "50", f"期望50，实际{result_b1['custom_slots']['number_value']}"
    assert result_b1["custom_slots"]["construct_word"] == "亮度调整为", f"期望亮度调整为，实际{result_b1['custom_slots']['construct_word']}"
    print("  [PASS] '将悬浮灯带亮度调整为50' 匹配成功")

    # 测试2: "将悬浮灯带亮度调整到最亮"
    result_b2 = matcher_brightness.match_template("{request_word} {deviceName} {construct_word} {brightness_value}", "将悬浮灯带亮度调整到最亮")
    assert result_b2 is not None, "应该匹配"
    assert result_b2["custom_slots"]["brightness_value"] == "最亮", f"期望最亮，实际{result_b2['custom_slots']['brightness_value']}"
    assert result_b2["custom_slots"]["construct_word"] == "亮度调整到", f"期望亮度调整到，实际{result_b2['custom_slots']['construct_word']}"
    print("  [PASS] '将悬浮灯带亮度调整到最亮' 匹配成功")

    # 测试3: "把卧室灯亮度调到高"
    result_b3 = matcher_brightness.match_template("{request_word} {deviceName} {construct_word} {brightness_value}", "把卧室灯亮度调到高")
    assert result_b3 is not None, "应该匹配"
    assert result_b3["custom_slots"]["brightness_value"] == "高", f"期望高，实际{result_b3['custom_slots']['brightness_value']}"
    assert result_b3["custom_slots"]["construct_word"] == "亮度调到", f"期望亮度调到，实际{result_b3['custom_slots']['construct_word']}"
    print("  [PASS] '把卧室灯亮度调到高' 匹配成功")

    # 测试4: "客厅吊灯80%"
    result_b4 = matcher_brightness.match_template("{deviceName}{number_value}%", "客厅吊灯80%")
    assert result_b4 is not None, "应该匹配"
    assert result_b4["custom_slots"]["number_value"] == "80", f"期望80，实际{result_b4['custom_slots']['number_value']}"
    print("  [PASS] '客厅吊灯80%' 匹配成功")

    print("\\n=== 亮度控制命令测试通过！===\\n")

    # ========== 关闭操作专项测试 ==========
    print("\\n=== 关闭操作映射测试 ===")

    # 测试数据：关闭相关操作词
    test_cases = [
        ("关闭左筒灯", "turn_off"),
        ("关左筒灯", "turn_off"),
        ("关上左筒灯", "turn_off"),
        ("停止左筒灯", "turn_off"),
        ("关闭客厅吊灯", "turn_off"),
        ("请关闭厨房筒灯", "turn_off"),
    ]

    # 使用mock设备（与主测试相同）
    mock_devices = [
        {"names": "左筒灯", "areas": "客厅", "device_class": "switch"},
        {"names": "右筒灯", "areas": "客厅", "device_class": "switch"},
        {"names": "客厅吊灯", "areas": "客厅", "device_class": "switch"},
        {"names": "厨房筒灯", "areas": "厨房", "device_class": "switch"},
    ]

    # 使用与主测试相同的插件实例
    all_passed = True
    for cmd, expected_action in test_cases:
        result = plugin.process(cmd, mock_devices)
        actual_action = result.get("action")
        if actual_action == expected_action:
            print(f"  [PASS] '{cmd}' → {expected_action}")
        else:
            print(f"  [FAIL] '{cmd}' → {actual_action} (期望 {expected_action})")
            all_passed = False

    if all_passed:
        print("\\n[PASS] 所有关闭操作测试通过！")
    else:
        print("\\n[FAIL] 部分关闭操作测试失败！")

except Exception as e:
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    traceback.print_exc()
    sys.exit(1)