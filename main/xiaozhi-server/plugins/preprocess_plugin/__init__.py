"""
预处理插件 - 智能家居指令预处理和意图识别

功能：
1. 模板匹配（基于操作分类）
2. 设备匹配（规则链）
3. 动态拦截（处理用户输入）
4. MCP函数注册（get_devices, turn_on_device, turn_off_device）

核心规则（11条）：
1. 操作独立模板
2. 设备列表构建
3. 设备类别支持
4. 操作匹配
5. Slots定义
6. 动态匹配
7. 响应随机
8. 默认区域限制
9. 默认设备
10. 无默认设备时全部
11. all_word处理
"""

import re
import yaml
import logging
import aiohttp
import random
import asyncio
from typing import Dict, List, Optional, Any
from plugins_func.register import Action, ActionResponse
from plugins.base import BasePlugin, PluginAction


class TemplateMatcher:
    """统一的模板匹配器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.action_mapping = config.get("action_mapping", {})

        # 统一的 slots 注册表
        # 格式：{slot_name: match_function}
        self.slot_registry = {}

        # 从 YAML 注册静态 slots
        self._register_static_slots()

    def _register_static_slots(self):
        """从 YAML 配置注册静态 slots"""
        slots_config = self.config.get("slots_config", {})

        # 注册 request_word（可选）- 使用工厂函数避免闭包问题
        if "request_word" in slots_config:
            words = slots_config["request_word"]
            def make_request_word_matcher(w):
                return lambda remaining: self._match_from_list(remaining, w, is_optional=True)
            self.slot_registry["request_word"] = make_request_word_matcher(words)

        # 注册 all_word（可选）- 使用工厂函数避免闭包问题
        if "all_word" in slots_config:
            words = slots_config["all_word"]
            def make_all_word_matcher(w):
                return lambda remaining: self._match_from_list(remaining, w, is_optional=True)
            self.slot_registry["all_word"] = make_all_word_matcher(words)

        # 注册其他自定义 slots
        for slot_name, slot_config in slots_config.items():
            if slot_name in ["request_word", "all_word"]:
                continue  # 已处理

            # 字典格式支持（如 brightness_value: {"高": 80, "中": 50}）
            if isinstance(slot_config, dict):
                def make_dict_matcher(config):
                    return lambda remaining: self._match_from_dict_keys(remaining, config)
                self.slot_registry[slot_name] = make_dict_matcher(slot_config)

            # 普通列表格式（如 construct_word: ["调整为", "设置为"]）
            elif isinstance(slot_config, list):
                def make_list_matcher(config):
                    return lambda remaining: self._match_from_list(remaining, config, is_optional=False)
                self.slot_registry[slot_name] = make_list_matcher(slot_config)

            # NUMBER 格式（如 number_value: "NUMBER"）
            elif isinstance(slot_config, str) and slot_config == "NUMBER":
                self.slot_registry[slot_name] = lambda remaining: self._match_number(remaining)

            # 未知格式，跳过
            else:
                pass

    def register_dynamic_slot(self, slot_name: str, match_values: List[str], is_optional: bool = False):
        """
        动态注册 slot（用于 area 和 deviceName）

        Args:
            slot_name: slot 名称，如 "area", "deviceName"
            match_values: 可匹配的值列表
            is_optional: 是否可选
        """
        # 使用工厂函数避免闭包捕获问题
        def make_matcher(values, optional):
            return lambda remaining: self._match_from_list(remaining, values, optional)
        self.slot_registry[slot_name] = make_matcher(match_values, is_optional)

    def _match_from_list(self, remaining: str, values: List[str], is_optional: bool = False) -> tuple:
        """
        统一的匹配方法：从列表中匹配

        Returns:
            (matched_text: str, is_matched: bool)
        """
        # 按长度降序排序，优先匹配长词
        sorted_values = sorted(values, key=len, reverse=True)

        for value in sorted_values:
            if remaining.startswith(value):
                return value, True

        # 未匹配
        return "", False

    def _match_from_dict_keys(self, remaining: str, key_value_dict: Dict[str, Any]) -> tuple:
        """
        从字典的key中匹配（用于 brightness_value 等）

        Args:
            remaining: 剩余字符串
            key_value_dict: {"最亮": 100, "高": 80, ...}

        Returns:
            (matched_key: str, is_matched: bool)
            返回匹配到的key，如 "高"
        """
        # 按key长度降序排序，优先匹配长词
        sorted_keys = sorted(key_value_dict.keys(), key=len, reverse=True)

        for key in sorted_keys:
            if remaining.startswith(key):
                return key, True

        return "", False

    def _match_number(self, remaining: str) -> tuple:
        """
        匹配 NUMBER 格式（任意数字）

        Args:
            remaining: 剩余字符串

        Returns:
            (matched_number: str, is_matched: bool)
        """
        # 匹配开头的数字（整数或小数）
        match = re.match(r'^(\d+(?:\.\d+)?)', remaining)
        if match:
            return match.group(1), True
        return "", False

    def match_template(self, template: str, command: str) -> Optional[Dict]:
        """
        严格按模板顺序匹配（支持字面量文本）

        核心逻辑：
        1. 解析模板得到占位符和字面量的混合序列
        2. 按顺序逐个匹配，操作剩余字符串
        3. 验证剩余为空

        模板格式：
        - "{placeholder}" - 占位符，从 slot_registry 匹配
        - "literal_text" - 字面量，必须精确匹配
        - 混合示例: "{deviceName} {number_value}%" → deviceName + number_value + "%"

        可选 slot 处理：
        - 如果 slot 是可选的（is_optional=True）且不匹配，继续下一个
        - 如果 slot 是必需的且不匹配，返回 None
        """
        remaining = command
        extraction = {
            "device_name": None,
            "area": None,
            "has_all_word": False,
            "has_request_word": False,
            "custom_slots": {}  # 新增：存储自定义slots
        }

        # 解析模板为混合序列：占位符和字面量
        # 示例: "{deviceName} {number_value}%" → ["{deviceName}", " ", "{number_value}", "%"]
        # 使用正则分割，保留占位符和字面量
        parts = re.split(r'(\{\w+\})', template)
        parts = [p for p in parts if p]  # 移除空字符串

        for part in parts:
            if part.startswith('{') and part.endswith('}'):
                # 占位符处理
                slot_name = part[1:-1]  # 移除花括号

                if slot_name == "action_word":
                    # action 需要特殊处理：映射到实际操作
                    action, action_text = self._extract_action(remaining)
                    if not action:
                        return None  # action 是必需的
                    remaining = remaining[len(action_text):].strip()
                    extraction["action"] = action
                    extraction["action_text"] = action_text

                elif slot_name in self.slot_registry:
                    # 使用统一的注册表匹配
                    matched, is_matched = self.slot_registry[slot_name](remaining)

                    if not is_matched:
                        # 检查是否是可选的
                        # request_word 和 all_word 默认可选
                        if slot_name in ["request_word", "all_word"]:
                            # 可选，继续下一个
                            continue
                        else:
                            # 对于其他slots，检查是否在slots_config中定义为可选
                            # 目前先视为必需，匹配失败
                            return None

                    if matched:
                        remaining = remaining[len(matched):].strip()

                        # 记录提取结果
                        if slot_name == "deviceName":
                            extraction["device_name"] = matched
                        elif slot_name == "area":
                            extraction["area"] = matched
                        elif slot_name == "request_word":
                            extraction["has_request_word"] = True
                        elif slot_name == "all_word":
                            extraction["has_all_word"] = True
                        else:
                            # 自定义 slot - 存储到 custom_slots
                            extraction["custom_slots"][slot_name] = matched

                else:
                    # 未知占位符
                    return None
            else:
                # 字面量处理 - 必须精确匹配
                literal = part

                # 特殊处理：空格字面量作为可选分隔符，不强制匹配
                if literal == " ":
                    # 如果剩余字符串以空格开头，消耗它
                    if remaining.startswith(" "):
                        remaining = remaining[1:]
                    # 继续下一个，不强制要求空格存在
                    continue

                # 普通字面量处理：先 trim 掉字面量和剩余字符串的空格，再精确匹配
                literal_trimmed = literal.strip()
                if not literal_trimmed:
                    continue  # 空字面量跳过

                # 剩余字符串也 trim 前导空格后匹配
                remaining_trimmed = remaining.lstrip()
                if not remaining_trimmed.startswith(literal_trimmed):
                    return None  # 字面量不匹配

                # 匹配成功，移除匹配的部分和后续空格
                match_len = len(literal_trimmed)
                remaining = remaining_trimmed[match_len:].lstrip()

        # 关键：验证剩余字符为空
        if remaining:
            return None

        return extraction

    def _extract_action(self, remaining: str) -> tuple:
        """提取动作（action, action_text）"""
        action_words = []
        for action, words in self.action_mapping.items():
            for word in words:
                action_words.append((word, action))

        # 按长度降序排序
        action_words.sort(key=lambda x: len(x[0]), reverse=True)

        for word, action in action_words:
            if remaining.startswith(word):
                return action, word

        return None, None



class PreprocessPlugin(BasePlugin):
    """智能家居指令预处理插件"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.name = "PreprocessPlugin"
        self.description = "智能家居设备控制预处理插件"

        # 加载配置
        self.config = self._load_intents_config()

        # 创建统一的模板匹配器
        self.template_matcher = TemplateMatcher(self.config)

        # 设备相关数据
        self.device_list_cache = []
        self.device_list_initialized = False
        self.device_substrings = []  # 设备子串字典
        self.device_areas = set()     # 设备区域集合

        # 设备API配置（从YAML加载，无默认值）
        device_api_config = self.config.get("device_api", {})
        self.device_list_url = device_api_config["device_list_url"]
        self.device_control_url = device_api_config["device_control_url"]
        self.device_api_headers = device_api_config["headers"]
        self.device_api_timeout = device_api_config["timeout"]

        # 首次交互标志位
        self.has_processed = False

        # 异步初始化（统一初始化设备列表、区域和子串字典）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._initialize_devices())
        except RuntimeError:
            self.logger.info("未检测到运行中的事件循环，设备列表将在首次调用时同步获取")

    def process(self, text: str, devices: List[Dict]) -> Dict[str, Any]:
        """
        主处理流程 - 支持模板回溯的版本

        处理流程:
        1. 命令映射处理（最高优先级）
        2. 模板匹配 + 设备验证回溯
           - 按顺序尝试每个模板
           - 模板匹配成功后验证设备有效性
           - 如果无效，继续尝试下一个模板
        3. 未匹配处理
        """
        try:
            # 1. 命令映射检查（最高优先级）
            mapped = self._process_command_mappings(text, devices)
            if mapped and mapped.get("processed"):
                return mapped

            processed_text = mapped.get("text", text) if mapped else text

            # 2. 模板匹配 + 设备验证回溯（核心逻辑）
            result = self._match_with_device_validation(processed_text, devices)
            if result:
                return result

            # 3. 未匹配处理
            return {
                "processed": False,
                "response": None,
                "reason": "未识别到有效操作"
            }
        except Exception as e:
            self.logger.error(f"处理用户输入时出错: {e}")
            return {
                "processed": False,
                "response": None,
                "reason": f"处理失败: {str(e)}"
            }

    def _match_with_device_validation(self, text: str, devices: List[Dict]) -> Optional[Dict]:
        """
        模板匹配 + 设备验证回溯

        核心逻辑：
        1. 遍历所有操作的模板
        2. 使用统一匹配器严格按模板顺序匹配
        3. 模板匹配成功后，验证设备是否存在且有效
        4. 如果设备有效，返回结果
        5. 如果设备无效，继续尝试下一个模板
        6. 所有模板都失败，返回 None
        """
        templates = self.config.get("operation_templates", {})

        # 按操作遍历模板
        for action, template_list in templates.items():
            for template in template_list:
                # 严格顺序匹配
                extraction = self.template_matcher.match_template(template, text)

                if extraction is None:
                    continue  # 模板不匹配，尝试下一个

                # 模板匹配成功，提取信息
                # 优先使用extraction中的action（如果模板包含action_word）
                extracted_action = extraction.get("action")
                if extracted_action:
                    action = extracted_action  # 使用提取的action，覆盖外层循环的action

                device_name = extraction.get("device_name")
                area = extraction.get("area")
                has_all_word = extraction.get("has_all_word", False)

                # 获取匹配设备
                matched_devices = self._find_devices_by_name_and_area(device_name, None, devices)

                # 设备列表分支处理
                if len(matched_devices) == 1:
                    pass  # 唯一设备，继续
                elif len(matched_devices) > 1 and has_all_word:
                    pass  # 有 all_word，继续
                elif len(matched_devices) > 1 and not has_all_word:
                    matched_devices = self._filter_by_area(matched_devices, area, devices)

                # 操作支持检查
                supported_devices = self._filter_supported_devices(matched_devices, action)

                if not supported_devices:
                    # 设备不支持该操作，继续尝试下一个模板
                    continue

                # 默认设备处理
                # 规则：如果命令包含 all_word（全部/所有/都），跳过默认设备规则
                if has_all_word:
                    final_devices = supported_devices
                else:
                    final_devices = self._apply_default_device_rule(supported_devices)

                if not final_devices:
                    # 没有最终设备，继续尝试下一个模板
                    continue

                # 成功！生成响应
                response = self._generate_response(action, extraction, final_devices)

                # API调用（异步）- 取消action判断，支持任意扩展
                try:
                    loop = asyncio.get_running_loop()
                    device_names = [d.get("names") for d in final_devices]
                    # 获取value值
                    value = self._get_value("value", extraction, final_devices)
                    loop.create_task(self._call_device_api(action, device_names, value))
                except RuntimeError:
                    pass

                return {
                    "processed": True,
                    "response": response,
                    "action": action,
                    "devices": [d.get("names") for d in final_devices]
                }

        # 所有模板都尝试过了，都没有成功
        # 检查是否需要回复 no_match 还是放行LLM
        reply_on_no_match = self.config.get("global", {}).get("reply_on_no_match", False)
        if reply_on_no_match:
            response = self._get_response("no_match", {}, [])
            return {
                "processed": True,
                "response": response,
                "action": None,
                "devices": []
            }
        else:
            # 放行LLM
            return {
                "processed": True,
                "response": "",
                "action": None,
                "devices": []
            }

    def _get_all_areas(self, devices: List[Dict]) -> set:
        """从设备列表提取所有唯一区域"""
        return {d.get("areas", "") for d in devices if d.get("areas")}

    def _find_devices_by_name_and_area(self, device_name: str, area: Optional[str], devices: List[Dict]) -> List[Dict]:
        """
        根据设备名称和区域查找设备

        优先级：
        1. 如果有区域，先按区域过滤，再按设备名匹配
        2. 如果无区域，按设备名匹配所有设备
        """
        # None检查：如果device_name为None，返回空列表
        if not device_name:
            return []

        if area:
            # 有区域，先过滤区域，再匹配设备名
            devices_in_area = [d for d in devices if d.get("areas") == area]
            return [d for d in devices_in_area if device_name in d.get("names", "")]
        else:
            # 无区域，匹配所有设备
            return [d for d in devices if device_name in d.get("names", "")]

    def _filter_by_area(self, matched_devices: List[Dict], area: Optional[str], all_devices: List[Dict]) -> List[Dict]:
        """
        区域过滤（规则8）

        5.1 有 area → 根据 area 过滤
        5.2 无 area → 根据 default_area 过滤（如果 restrict_to_default_area=true）
        """
        if area:
            # 有指定区域，按区域过滤
            return [d for d in matched_devices if d.get("areas") == area]

        # 无指定区域，检查是否需要默认区域限制
        restrict_to_default = self.config.get("global", {}).get("restrict_to_default_area", False)
        if restrict_to_default:
            default_area = self.config.get("global", {}).get("default_area", "")
            return [d for d in matched_devices if d.get("areas") == default_area]

        # 不限制，默认返回所有匹配
        return matched_devices

    def _filter_supported_devices(self, devices: List[Dict], action: str) -> List[Dict]:
        """
        操作支持检查 - 根据设备的 device_class 判断是否支持该操作

        从配置文件中读取 device_class_operations 获取支持的操作映射
        """
        # 从配置中读取设备类别支持的操作映射
        support_map = self.config.get("device_class_operations", {})

        supported = []
        for device in devices:
            device_class = device.get("device_class", "")

            if device_class in support_map:
                if action in support_map[device_class]:
                    supported.append(device)
            else:
                # 未知设备类别，保守处理：不支持任何操作
                pass

        return supported

    def _apply_default_device_rule(self, matched_devices: List[Dict]) -> List[Dict]:
        """
        规则9,10: 默认设备规则

        规则9: 如果有默认设备配置，只返回默认设备（精准匹配）
        规则10: 如果无默认设备，或默认设备不在匹配列表中，返回所有匹配设备
        """
        if not matched_devices:
            return []

        default_devices = self.config.get("default_devices", [])
        if not default_devices:
            # 规则10: 无默认设备配置，返回所有匹配
            return matched_devices

        # 规则9: 有默认设备，精准匹配
        result = []
        matched_names = {d.get("names", "") for d in matched_devices}

        for default_name in default_devices:
            # 精准匹配: 默认设备名必须完全存在于匹配设备中
            if default_name in matched_names:
                for device in matched_devices:
                    if device.get("names") == default_name:
                        result.append(device)

        # 规则10: 如果默认设备都不在匹配设备中，返回所有匹配设备
        if not result:
            return matched_devices

        return result

    def _get_response(self, key: str, extraction: Dict, devices: List[Dict]) -> str:
        """
        从响应模板中随机选择一个并替换占位符

        Args:
            key: 响应类型（如 "set_brightness"）
            extraction: 模板匹配结果（JSON）
            devices: 设备列表

        Returns:
            处理后的响应消息
        """
        responses = self.config.get("responses", {}).get(key, [])
        if not responses:
            return ""

        template = random.choice(responses)
        result = template

        # 查找所有占位符
        placeholders = re.findall(r'\{(\w+)\}', template)

        # 统一替换所有占位符
        for placeholder in placeholders:
            value = self._get_value(placeholder, extraction, devices)
            result = result.replace(f"{{{placeholder}}}", value)

        return result

    def _unify_values(self, extraction: Dict) -> Dict:
        """
        将所有 xxx_value 统一为 value

        例如：
        - {"custom_slots": {"brightness_value": "高"}} → {"value": "高"}
        - {"custom_slots": {"number_value": "50"}} → {"value": "50"}
        - {"custom_slots": {"brightness_value": "高", "number_value": "50"}} → {"value": "高"}

        Returns:
            包含 value 字段的 unified extraction
        """
        result = extraction.copy()
        result["value"] = ""

        # 从 custom_slots 提取值（优先级：brightness_value > number_value > 其他）
        custom_slots = extraction.get("custom_slots", {})

        # 查找所有以 _value 结尾的 key
        if not result["value"]:
            for key, value in custom_slots.items():
                if key.endswith("_value"):
                    result["value"] = str(value)
                    break

        return result

    def _get_value(self, key: str, extraction: Dict, devices: List[Dict]) -> str:
        """
        从extraction和devices中获取值（统一值获取函数）

        Args:
            key: 占位符名称，如 "deviceName", "value"
            extraction: 模板匹配结果（JSON）
            devices: 设备列表

        Returns:
            获取到的值，获取不到返回空字符串
        """
        # 1. 统一值占位符 {value}
        if key == "value":
            unified = self._unify_values(extraction)
            return unified.get("value", "")

        # 2. 内置占位符
        if key == "deviceName":
            names = [d.get("names", "") for d in devices]
            return names[0] if len(names) == 1 else "、".join(names)

        if key == "devices":
            names = [d.get("names", "") for d in devices]
            return "、".join(names)

        # 3. 向后兼容：旧版占位符（brightness_value, number_value 等）
        custom_slots = extraction.get("custom_slots", {})
        if key in custom_slots:
            return str(custom_slots[key])

        # 4. 其他字段（直接从 extraction 获取）
        if key in extraction:
            value = extraction[key]
            if isinstance(value, bool):
                return ""  # 布尔值不返回，返回空字符串
            return str(value)

        # 5. 获取不到，返回空字符串
        return ""

    def _remove_punctuation(self, text: str) -> str:
        """
        移除文本中的标点符号，避免语音识别的标点符号影响识别

        Args:
            text: 原始文本

        Returns:
            移除标点符号后的文本
        """
        # 定义需要移除的标点符号
        # 包括：中文标点、英文标点、以及其他常见符号
        punctuation = r'''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~！“”‘’（）【】《》？，。；：、·～'''

        # 使用正则表达式移除所有标点符号
        result = re.sub(f'[{re.escape(punctuation)}]', '', text)

        # 移除多余的空白字符（包括空格、制表符、换行符等）
        result = re.sub(r'\s+', '', result)

        return result

    def _generate_response(self, action: str, extraction: Dict, devices: List[Dict]) -> str:
        """生成响应（使用随机模板）"""
        return self._get_response(action, extraction, devices)

    async def pre_process_text(self, conn, text):
        """
        插件入口 - 保留三态逻辑

        返回:
            (response_text, PluginAction)
        """
        # 移除标点符号，避免语音识别的标点符号影响识别
        text = self._remove_punctuation(text)

        devices = await self._fetch_entities(conn)
        result = self.process(text, devices)

        # 获取连续对话配置
        allow_continuous = self.config.get("global", {}).get("allow_continuous_conversation", True)

        # 状态1: 成功匹配 + 有设备 → 执行并根据配置决定返回状态
        if result["processed"] and result.get("devices"):
            if allow_continuous:
                # 允许连续对话：INTERCEPT，不关闭连接
                return result["response"], PluginAction.INTERCEPT
            else:
                # 单次对话：CLOSE，关闭连接
                return result["response"], PluginAction.CLOSE

        # 状态2&3: 失败或不确定 → 放行给LLM
        # 仅首次交互附加设备信息和系统指令，后续依赖上下文
        if not self.has_processed:
            system_instruct = self._get_system_instruct()
            devices_info = self._generate_devices_info_format(devices)
            prompt = f"{system_instruct}\n\n{devices_info}\n\n{text}"
            self.has_processed = True
        else:
            prompt = text
        return prompt, PluginAction.RELEASE

    # ========== 保留的方法 ==========

    def _load_intents_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "intents.yaml")
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}

    def _process_command_mappings(self, text: str, devices: List[Dict]) -> Optional[Dict]:
        """命令映射处理（最高优先级）"""
        text = text.strip()
        mappings = self.config.get("command_mappings") or {}

        # 新格式：{command: {action: "...", devices: [...]}}
        if text in mappings:
            mapping = mappings[text]
            action = mapping.get("action")
            device_names = mapping.get("devices", [])

            # 查找匹配的设备对象 - 精确匹配
            matched_devices = []
            for name in device_names:
                for device in devices:
                    if device.get("names") == name:
                        matched_devices.append(device)
                        break

            if matched_devices:
                # 生成响应
                # 命令映射不需要extraction，创建空字典
                extraction = {"custom_slots": {}}
                response = self._generate_response(action, extraction, matched_devices)

                # API调用（异步）- 执行设备控制
                try:
                    loop = asyncio.get_running_loop()
                    device_names_list = [d.get("names") for d in matched_devices]
                    # 命令映射没有value参数
                    loop.create_task(self._call_device_api(action, device_names_list, ""))
                except RuntimeError:
                    pass

                return {
                    "processed": True,
                    "response": response,
                    "action": action,
                    "devices": [d.get("names") for d in matched_devices]
                }

        return {"text": text}

    async def _call_device_api(self, action: str, device_names: List[str], value: str = ""):
        """
        统一的设备控制API调用

        Args:
            action: 操作类型（支持任意扩展）
            device_names: 设备名称列表
            value: 操作值（如亮度值）
        """
        # 统一请求体格式
        data = {
            "action": action,
            "devices": device_names,
            "value": value
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.device_api_timeout)) as session:
                async with session.post(
                    self.device_control_url,
                    headers=self.device_api_headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 400:
                        error_text = await response.text()
                        self.logger.error(f"设备控制API 400错误: {error_text}")
                        return None
                    else:
                        self.logger.error(f"设备控制API返回状态码 {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"设备控制API调用异常: {e}")
            return None

    async def _initialize_devices(self):
        """初始化设备列表、区域和子串字典"""
        devices = await self._fetch_entities(None)
        if not devices:
            return

        # 缓存设备列表
        self.device_list_cache = devices
        self.device_list_initialized = True

        # 提取所有区域
        self.device_areas = {d.get("areas", "") for d in devices if d.get("areas")}

        # 生成设备子串字典
        all_names = {d.get("names", "") for d in devices if d.get("names")}
        substrings = set()

        for name in all_names:
            length = len(name)
            for i in range(length):
                for j in range(i + 1, length + 1):
                    substrings.add(name[i:j])

        self.device_substrings = sorted(list(substrings), key=len, reverse=True)

        # 动态注册 area 和 deviceName slot
        if self.device_areas:
            self.template_matcher.register_dynamic_slot(
                "area",
                list(self.device_areas),
                is_optional=False
            )

        if self.device_substrings:
            self.template_matcher.register_dynamic_slot(
                "deviceName",
                self.device_substrings,
                is_optional=False
            )

        self.logger.info(f"设备初始化完成：{len(devices)} 个设备，{len(self.device_areas)} 个区域，{len(self.device_substrings)} 个子串")

    async def _fetch_entities(self, conn):
        """获取设备列表"""
        if self.device_list_initialized and self.device_list_cache:
            return self.device_list_cache

        self.logger.info("设备列表未初始化，尝试同步获取...")
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.device_api_timeout)) as session:
                async with session.post(
                    self.device_list_url,
                    headers=self.device_api_headers,
                    json={}  # 请求体为空
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # 设备列表格式: {"data": [...]}
                        if isinstance(result, dict):
                            device_list = result.get("data", [])
                            if isinstance(device_list, list):
                                self.device_list_cache = device_list
                                self.device_list_initialized = True
                                self.logger.info(f"同步获取设备列表成功，共 {len(device_list)} 个设备")
                                return device_list
                            else:
                                self.logger.error(f"设备获取API返回格式错误，data字段不是list: {type(device_list)}")
                                return []
                        else:
                            self.logger.error(f"设备获取API返回格式错误，期望dict，实际: {type(result)}")
                            return []
                    elif response.status == 400:
                        error_text = await response.text()
                        self.logger.error(f"设备获取API返回400错误: {error_text}")
                        return []
                    else:
                        self.logger.error(f"设备获取API返回错误状态码: {response.status}")
                        return []
        except asyncio.TimeoutError:
            self.logger.error("同步获取设备列表时出错：请求超时")
        except Exception as e:
            self.logger.error(f"同步获取设备列表时出错: {e}")

        return []

    def _generate_devices_info_format(self, devices):
        """生成 <devices_info> 格式的设备信息 ⭐ 关键保留"""
        default_area = self.config.get("default_area", {}).get("name", "")

        if not devices:
            return f"<default_area>{default_area}</default_area>\n<devices_info>\n无设备信息\n</devices_info>"

        lines = [f"<default_area>{default_area}</default_area>", "<devices_info>"]
        for device in devices:
            name = device.get("names", "") if isinstance(device.get("names"), str) else device.get("name", "")
            area = device.get("areas", "") if isinstance(device.get("areas"), str) else device.get("area", "")
            state = device.get("state", "")
            dtype = device.get("device_class", "switch")  # 只使用 device_class

            # 格式化状态
            if isinstance(state, bool):
                state_desc = "开启" if state else "关闭"
            elif state == "on":
                state_desc = "开启"
            elif state == "off":
                state_desc = "关闭"
            else:
                state_desc = str(state)

            lines.append(f"{name}，{area}，{state_desc}，{dtype}")

        lines.append("</devices_info>")
        return "\n".join(lines)

    def _get_system_instruct(self) -> str:
        """
        获取系统指令，支持灵活的占位符替换

        支持的占位符格式：
        1. 配置路径占位符：{global.default_area}、{device_class_operations} 等
           会从 self.config 中读取对应路径的值

        2. 自定义占位符：{custom_placeholder}
           会从 system_instruct_placeholders 配置中读取

        Returns:
            处理后的系统指令文本
        """
        instruct = self.config.get("system_instruct", "")
        if not instruct:
            return ""

        # 获取自定义占位符映射
        placeholders_map = self.config.get("system_instruct_placeholders", {})

        # 查找所有占位符 {xxx}
        placeholders = re.findall(r'\{([^}]+)\}', instruct)

        # 替换占位符
        result = instruct
        for placeholder in placeholders:
            # 优先从自定义占位符映射中查找
            if placeholder in placeholders_map:
                value = placeholders_map[placeholder]
                if isinstance(value, (dict, list)):
                    value = str(value)
                result = result.replace(f"{{{placeholder}}}", str(value))
            else:
                # 尝试从配置中按路径查找（如 global.default_area）
                value = self._get_config_by_path(placeholder)
                if value is not None:
                    if isinstance(value, (dict, list)):
                        value = str(value)
                    result = result.replace(f"{{{placeholder}}}", str(value))

        return result

    def _get_config_by_path(self, path: str) -> Any:
        """
        根据路径从配置中获取值

        Args:
            path: 路径，如 "global.default_area" 或 "device_class_operations"

        Returns:
            配置值，如果不存在返回 None
        """
        parts = path.split(".")
        current = self.config

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        return current


# =============================================================================
# MCP 函数定义
# =============================================================================

from plugins.register import register_function, ToolType


_get_devices_desc = {
    "type": "function",
    "function": {
        "name": "get_devices",
        "description": "获取当前系统中的所有设备列表",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

_turn_on_desc = {
    "type": "function",
    "function": {
        "name": "turn_on_device",
        "description": "打开指定的一个或多个设备",
        "parameters": {
            "type": "object",
            "properties": {
                "devices": {"type": "array", "items": {"type": "string"}, "description": "设备名称数组"}
            },
            "required": ["devices"]
        }
    }
}

_turn_off_desc = {
    "type": "function",
    "function": {
        "name": "turn_off_device",
        "description": "关闭指定的一个或多个设备",
        "parameters": {
            "type": "object",
            "properties": {
                "devices": {"type": "array", "items": {"type": "string"}, "description": "设备名称数组"}
            },
            "required": ["devices"]
        }
    }
}

_set_brightness_desc = {
    "type": "function",
    "function": {
        "name": "set_brightness",
        "description": "设置设备的亮度值",
        "parameters": {
            "type": "object",
            "properties": {
                "devices": {"type": "array", "items": {"type": "string"}, "description": "设备名称数组"},
                "value": {"type": "number", "description": "亮度值，范围1-100"}
            },
            "required": ["devices", "value"]
        }
    }
}


# 异步版本的内部实现
async def _get_devices_async(conn):
    """异步获取设备列表 - 使用统一API调用"""
    plugin = PreprocessPlugin()
    devices = await plugin._fetch_entities(conn)
    if devices:
        return ActionResponse(Action.REQLLM, plugin._generate_devices_info_format(devices), None)
    else:
        return ActionResponse(Action.ERROR, None, "获取设备列表失败")


async def _turn_on_device_async(conn, devices):
    """异步打开设备 - 使用统一API调用"""
    if not isinstance(devices, list):
        devices = [devices]

    # 使用插件实例的统一API调用方法
    plugin = PreprocessPlugin()
    result = await plugin._call_device_api("turn_on", devices, "")

    if result:
        return ActionResponse(Action.REQLLM, f"已成功打开设备 {'、'.join(devices)}", None)
    return ActionResponse(Action.ERROR, None, "打开设备失败")


async def _turn_off_device_async(conn, devices):
    """异步关闭设备 - 使用统一API调用"""
    if not isinstance(devices, list):
        devices = [devices]

    # 使用插件实例的统一API调用方法
    plugin = PreprocessPlugin()
    result = await plugin._call_device_api("turn_off", devices, "")

    if result:
        return ActionResponse(Action.REQLLM, f"已成功关闭设备 {'、'.join(devices)}", None)
    return ActionResponse(Action.ERROR, None, "关闭设备失败")


async def _set_brightness_async(conn, devices, value):
    """异步设置亮度 - 使用统一API调用"""
    if not isinstance(devices, list):
        devices = [devices]

    # 使用插件实例的统一API调用方法
    plugin = PreprocessPlugin()
    result = await plugin._call_device_api("set_brightness", devices, str(value))

    if result:
        return ActionResponse(Action.REQLLM, f"已成功设置设备 {'、'.join(devices)} 亮度为 {value}", None)
    return ActionResponse(Action.ERROR, None, "设置亮度失败")


# 同步版本的MCP函数（用于直接注册）
# 直接返回协程对象，让ServerPluginExecutor.execute()去await
def _get_devices_sync(conn):
    """同步获取设备列表的MCP函数 - 返回协程"""
    return _get_devices_async(conn)


def _turn_on_device_sync(conn, devices):
    """同步打开设备的MCP函数 - 返回协程"""
    return _turn_on_device_async(conn, devices)


def _turn_off_device_sync(conn, devices):
    """同步关闭设备的MCP函数 - 返回协程"""
    return _turn_off_device_async(conn, devices)


def _set_brightness_sync(conn, devices, value):
    """同步设置亮度的MCP函数 - 返回协程"""
    return _set_brightness_async(conn, devices, value)


# 注册同步版本的MCP函数
@register_function("get_devices", _get_devices_desc, ToolType.IOT_CTL)
def get_devices(conn):
    """获取设备列表的MCP函数（同步版本）"""
    return _get_devices_sync(conn)


@register_function("turn_on_device", _turn_on_desc, ToolType.IOT_CTL)
def turn_on_device(conn, devices):
    """打开设备的MCP函数（同步版本）"""
    return _turn_on_device_sync(conn, devices)


@register_function("turn_off_device", _turn_off_desc, ToolType.IOT_CTL)
def turn_off_device(conn, devices):
    """关闭设备的MCP函数（同步版本）"""
    return _turn_off_device_sync(conn, devices)


@register_function("set_brightness", _set_brightness_desc, ToolType.IOT_CTL)
def set_brightness(conn, devices, value):
    """设置亮度的MCP函数（同步版本）"""
    return _set_brightness_sync(conn, devices, value)
