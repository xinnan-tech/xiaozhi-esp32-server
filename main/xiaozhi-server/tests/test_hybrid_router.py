import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _Logger:
    def bind(self, **kwargs):
        return self

    def info(self, message):
        pass

    def warning(self, message):
        pass


class _Provider:
    def __init__(self, decision=None, text="chat response"):
        self.decision = decision
        self.text = text
        self.function_calls = 0
        self.no_stream_calls = 0

    def response_no_stream(self, *args, **kwargs):
        self.no_stream_calls += 1
        return self.decision

    def response(self, *args, **kwargs):
        yield self.text

    def response_with_functions(self, *args, **kwargs):
        self.function_calls += 1
        yield self.text, None


config_module = types.ModuleType("config")
logger_module = types.ModuleType("config.logger")
logger_module.setup_logging = lambda: _Logger()
base_module = types.ModuleType("core.providers.llm.base")
base_module.LLMProviderBase = object
instances = {}
llm_utils_module = types.ModuleType("core.utils.llm")
llm_utils_module.create_instance = lambda provider_type, config: instances[provider_type]
sys.modules.setdefault("config", config_module)
sys.modules.setdefault("config.logger", logger_module)
sys.modules.setdefault("core", types.ModuleType("core"))
sys.modules.setdefault("core.providers", types.ModuleType("core.providers"))
sys.modules.setdefault("core.providers.llm", types.ModuleType("core.providers.llm"))
sys.modules.setdefault("core.providers.llm.base", base_module)
sys.modules.setdefault("core.utils", types.ModuleType("core.utils"))
sys.modules.setdefault("core.utils.llm", llm_utils_module)

PROVIDER_PATH = (
    Path(__file__).parents[1]
    / "core"
    / "providers"
    / "llm"
    / "hybrid_router"
    / "hybrid_router.py"
)
spec = importlib.util.spec_from_file_location("hybrid_router_provider", PROVIDER_PATH)
provider_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider_module)


class HybridRouterProviderTest(unittest.TestCase):
    def setUp(self):
        instances.clear()
        self.chat = _Provider(text="zgc answer")
        self.tool = _Provider(
            '{"name":"self.camera.take_photo","arguments":{"question":"拍一张照片"}}'
        )
        self.router = _Provider('{"route":"zgc_chat"}')
        instances.update(chat=self.chat, tool=self.tool, router=self.router)
        self.provider = provider_module.LLMProvider(
            {
                "chat_provider_type": "chat",
                "chat_provider_config": {},
                "tool_provider_type": "tool",
                "tool_provider_config": {},
                "router_provider_type": "router",
                "router_provider_config": {},
            }
        )

    def test_routes_valid_json_to_zgc(self):
        result = list(
            self.provider.response_with_functions(
                "session", [{"role": "user", "content": "介绍一下中关村"}], []
            )
        )
        self.assertEqual(result, [("zgc answer", None)])
        self.assertEqual(self.tool.function_calls, 0)

    def test_routes_valid_json_to_device_tools(self):
        self.router.decision = '{"route":"device_tool"}'
        functions = [
            {
                "type": "function",
                "function": {
                    "name": "self.camera.take_photo",
                    "description": "拍摄照片",
                    "parameters": {"type": "object"},
                },
            }
        ]
        result = list(
            self.provider.response_with_functions(
                "session", [{"role": "user", "content": "拍一张照片"}], functions
            )
        )
        content, tool_calls = result[0]
        self.assertIsNone(content)
        self.assertEqual(tool_calls[0].function.name, "self.camera.take_photo")
        self.assertEqual(
            tool_calls[0].function.arguments, '{"question": "拍一张照片"}'
        )
        self.assertEqual(self.tool.no_stream_calls, 1)

    def test_only_active_tool_result_skips_routing(self):
        self.router.decision = '{"route":"zgc_chat"}'
        result = list(
            self.provider.response_with_functions(
                "session",
                [
                    {"role": "user", "content": "拍一张照片"},
                    {"role": "tool", "content": "照片已拍摄"},
                ],
                [],
            )
        )
        self.assertEqual(result, [("zgc answer", None)])
        self.assertEqual(self.tool.no_stream_calls, 0)


if __name__ == "__main__":
    unittest.main()
