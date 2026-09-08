import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch, sentinel


class NullLogger:
    def bind(self, **kwargs):
        return self

    def debug(self, *args, **kwargs):
        pass

    info = debug
    error = debug
    warning = debug


def stub_module(name, **attributes):
    module = ModuleType(name)
    vars(module).update(attributes)
    return module


stubs = {
    "httpx": stub_module("httpx", Timeout=lambda *args, **kwargs: None),
    "openai": stub_module("openai", OpenAI=None),
    "openai.types": stub_module(
        "openai.types", CompletionUsage=type("Usage", (), {})
    ),
    "config.logger": stub_module("config.logger", setup_logging=lambda: NullLogger()),
    "core.utils.util": stub_module("core.utils.util", check_model_key=lambda *args: None),
    "core.providers.llm.base": stub_module(
        "core.providers.llm.base", LLMProviderBase=object
    ),
}
target = Path(__file__).parents[1] / "core/providers/llm/openai/openai.py"
spec = importlib.util.spec_from_file_location("openai_provider_under_test", target)
provider_module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, stubs):
    spec.loader.exec_module(provider_module)


class FakeStream:
    def __init__(self):
        delta = SimpleNamespace(content="角色化回复", tool_calls=None)
        self.chunks = [SimpleNamespace(choices=[SimpleNamespace(delta=delta)])]
        self.closed = False

    def __iter__(self):
        return iter(self.chunks)

    def close(self):
        self.closed = True


class FakeCompletions:
    def __init__(self):
        self.stream = FakeStream()
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return self.stream


class ClosableTokens:
    def __init__(self, tokens):
        self.tokens = tokens
        self.closed = False

    def __iter__(self):
        return iter(self.tokens)

    def close(self):
        self.closed = True


class OpenAIProviderTest(unittest.TestCase):
    def make_provider(self, enable_function_call=sentinel.missing):
        completions = FakeCompletions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        provider_module.openai.OpenAI = lambda **kwargs: client
        config = {
            "model_name": "test-model",
            "api_key": "test-key",
            "base_url": "http://localhost/v1",
        }
        if enable_function_call is not sentinel.missing:
            config["enable_function_call"] = enable_function_call
        return provider_module.LLMProvider(config), completions

    def test_default_true_and_blank_forward_tools(self):
        tools = [{"type": "function", "function": {"name": "get_time"}}]
        dialogue = [{"role": "system", "content": "你是湾湾小何"}]

        for value in (sentinel.missing, True, ""):
            with self.subTest(value=value):
                provider, completions = self.make_provider(value)
                result = list(provider.response_with_functions("sid", dialogue, tools))

                self.assertIs(completions.request["tools"], tools)
                self.assertIs(completions.request["messages"], dialogue)
                self.assertEqual(result, [("角色化回复", None)])
                self.assertTrue(completions.stream.closed)

    def test_disabled_function_call_closes_delegated_stream_on_early_stop(self):
        provider, _ = self.make_provider(False)
        delegated_stream = ClosableTokens(["第一段", "第二段"])

        with patch.object(provider, "response", return_value=delegated_stream):
            responses = provider.response_with_functions("sid", [])
            self.assertEqual(next(responses), ("第一段", None))
            responses.close()

        self.assertTrue(delegated_stream.closed)

    def test_function_call_disabled_uses_regular_response_as_tuples(self):
        dialogue = [{"role": "system", "content": "你是湾湾小何"}]

        for value in (False, "false"):
            with self.subTest(value=value):
                provider, completions = self.make_provider(value)
                with patch.object(provider, "response", wraps=provider.response) as response:
                    result = list(
                        provider.response_with_functions(
                            "sid", dialogue, [{}], max_tokens=42, temperature=0.3
                        )
                    )

                response.assert_called_once_with(
                    "sid", dialogue, max_tokens=42, temperature=0.3
                )
                self.assertNotIn("tools", completions.request)
                self.assertIs(completions.request["messages"], dialogue)
                self.assertEqual(completions.request["max_tokens"], 42)
                self.assertEqual(completions.request["temperature"], 0.3)
                self.assertEqual(result, [("角色化回复", None)])
                self.assertTrue(completions.stream.closed)
