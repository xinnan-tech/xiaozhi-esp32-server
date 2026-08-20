import json
import uuid
from types import SimpleNamespace

from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase
from core.utils.llm import create_instance


TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    """Route each user turn to ZGC chat or XiaoZhi's tool-capable LLM."""

    def __init__(self, config):
        self.chat_provider = create_instance(
            config["chat_provider_type"], config["chat_provider_config"]
        )
        self.tool_provider = create_instance(
            config["tool_provider_type"], config["tool_provider_config"]
        )
        router_config = config.get("router_provider_config", config["tool_provider_config"])
        router_type = config.get("router_provider_type", config["tool_provider_type"])
        self.router_provider = create_instance(router_type, router_config)
        self.router_max_tokens = int(config.get("router_max_tokens", 4096))
        self.tool_selection_max_tokens = int(
            config.get("tool_selection_max_tokens", 512)
        )

    @staticmethod
    def _last_user_text(dialogue):
        for message in reversed(dialogue):
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                return content
        return ""

    @staticmethod
    def _tool_summary(functions):
        entries = []
        for function in functions or []:
            definition = function.get("function", function)
            if not isinstance(definition, dict):
                continue
            name = definition.get("name")
            description = definition.get("description", "").replace("\n", " ")
            if name:
                entries.append(f"{name}: {description[:160]}")
        return "\n".join(entries) or "无"

    @staticmethod
    def _is_tool_result_turn(dialogue):
        """Only preserve the active tool-call chain, not old tool history."""
        for message in reversed(dialogue):
            role = message.get("role")
            if role in {"tool", "user"}:
                return role == "tool"
        return False

    @staticmethod
    def _tool_catalog(functions):
        catalog = []
        for function in functions or []:
            definition = function.get("function", function)
            if not isinstance(definition, dict):
                continue
            name = definition.get("name")
            if not name or name == "direct_answer":
                continue
            catalog.append(
                {
                    "name": name,
                    "description": definition.get("description", ""),
                    "parameters": definition.get(
                        "parameters", definition.get("inputSchema", {})
                    ),
                }
            )
        return catalog

    @staticmethod
    def _parse_tool_call(result, allowed_names):
        decoder = json.JSONDecoder()
        for index, char in enumerate(result or ""):
            if char != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(result[index:])
            except json.JSONDecodeError:
                continue
            name = payload.get("name")
            arguments = payload.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    return None
            if name in allowed_names and isinstance(arguments, dict):
                return name, arguments
        return None

    def _route(self, dialogue, functions):
        if self._is_tool_result_turn(dialogue):
            return "device_tool"

        prompt = (
            "你是 SparkBot 的请求路由器。根据当前用户请求和可用设备工具选择处理方。"
            "只有必须操作或读取设备状态才能完成的请求，才选择 device_tool；"
            "知识问答、闲聊、创作、解释、翻译及无法通过工具执行的请求选择 zgc_chat。"
            "只返回合法 JSON：{\"route\":\"device_tool\"} 或 {\"route\":\"zgc_chat\"}。"
        )
        context = (
            f"当前用户请求：{self._last_user_text(dialogue)}\n"
            f"可用设备工具：\n{self._tool_summary(functions)}"
        )
        try:
            result = self.router_provider.response_no_stream(
                prompt, context, max_tokens=self.router_max_tokens, temperature=0
            )
            payload = json.loads(result.strip())
            route = payload.get("route")
            if route in {"device_tool", "zgc_chat"}:
                logger.bind(tag=TAG).info(f"LLM router decision: {route}")
                return route
            raise ValueError("unknown route")
        except Exception as error:
            logger.bind(tag=TAG).warning(
                f"LLM router returned an invalid result; using ZGC: {error}"
            )
            return "zgc_chat"

    def response(self, session_id, dialogue, **kwargs):
        yield from self.chat_provider.response(session_id, dialogue, **kwargs)

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        if self._is_tool_result_turn(dialogue):
            for token in self.chat_provider.response(session_id, dialogue, **kwargs):
                yield token, None
            return

        if self._route(dialogue, functions) == "device_tool":
            catalog = self._tool_catalog(functions)
            if not catalog:
                yield "当前没有可用的设备工具。", None
                return

            prompt = (
                "你是 SparkBot 的设备工具选择器。当前请求已经确认需要操作设备。"
                "从工具目录中选择唯一最匹配的工具。只返回合法 JSON，格式为"
                '{"name":"工具名","arguments":{}}。'
                "name 必须严格来自工具目录；arguments 必须是对象；不要输出思考、Markdown 或解释。"
            )
            context = (
                f"当前用户请求：{self._last_user_text(dialogue)}\n"
                f"工具目录：{json.dumps(catalog, ensure_ascii=False)}"
            )
            try:
                result = self.tool_provider.response_no_stream(
                    prompt,
                    context,
                    max_tokens=self.tool_selection_max_tokens,
                    temperature=0,
                )
                selected = self._parse_tool_call(
                    result, {tool["name"] for tool in catalog}
                )
                if selected is None:
                    raise ValueError(f"invalid tool selector response: {result!r}")
                name, arguments = selected
                logger.bind(tag=TAG).info(f"LLM tool selection: {name}")
                call = SimpleNamespace(
                    id=uuid.uuid4().hex,
                    index=0,
                    function=SimpleNamespace(
                        name=name,
                        arguments=json.dumps(arguments, ensure_ascii=False),
                    ),
                )
                yield None, [call]
            except Exception as error:
                logger.bind(tag=TAG).warning(
                    f"LLM tool selection failed: {error}"
                )
                yield "设备指令暂时无法识别，请再说一次。", None
            return
        for token in self.chat_provider.response(session_id, dialogue, **kwargs):
            yield token, None
