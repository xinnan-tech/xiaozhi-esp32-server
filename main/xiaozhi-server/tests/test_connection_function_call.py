import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


def stub_module(name, **attributes):
    module = ModuleType(name)
    vars(module).update(attributes)
    return module


def noop(*args, **kwargs):
    pass


def dependency_stubs():
    error = type("StubError", (Exception,), {})
    return {
        "websockets": stub_module(
            "websockets", ServerConnection=type("ServerConnection", (), {})
        ),
        "opuslib_next": stub_module("opuslib_next"),
        "numpy": stub_module("numpy"),
        "core.utils.util": stub_module(
            "core.utils.util",
            extract_json_from_string=noop,
            check_vad_update=noop,
            check_asr_update=noop,
            filter_sensitive_info=noop,
            get_system_error_response=noop,
        ),
        "core.utils.modules_initialize": stub_module(
            "core.utils.modules_initialize",
            initialize_modules=noop,
            initialize_tts=noop,
            initialize_asr=noop,
        ),
        "core.handle.reportHandle": stub_module(
            "core.handle.reportHandle", report=noop, enqueue_tool_report=noop
        ),
        "core.providers.tts.default": stub_module(
            "core.providers.tts.default", DefaultTTS=object
        ),
        "core.handle.textHandle": stub_module(
            "core.handle.textHandle", handleTextMessage=noop
        ),
        "core.providers.tools.unified_tool_handler": stub_module(
            "core.providers.tools.unified_tool_handler", UnifiedToolHandler=object
        ),
        "plugins_func.loadplugins": stub_module(
            "plugins_func.loadplugins", auto_import_modules=noop
        ),
        "plugins_func.register": stub_module(
            "plugins_func.register",
            Action=SimpleNamespace(ERROR=-1),
            ActionResponse=object,
            all_function_registry={},
            module_func_map={},
        ),
        "core.auth": stub_module("core.auth", AuthenticationError=error),
        "config.config_loader": stub_module(
            "config.config_loader", get_private_config_from_api=noop
        ),
        "config.logger": stub_module(
            "config.logger",
            setup_logging=noop,
            build_module_string=noop,
            create_connection_logger=noop,
        ),
        "config.manage_api_client": stub_module(
            "config.manage_api_client",
            DeviceNotFoundException=error,
            DeviceBindException=error,
            generate_and_save_chat_title=noop,
        ),
        "core.utils.prompt_manager": stub_module(
            "core.utils.prompt_manager", PromptManager=object
        ),
        "core.utils.voiceprint_provider": stub_module(
            "core.utils.voiceprint_provider", VoiceprintProvider=object
        ),
    }


server_root = Path(__file__).parents[1]
target = server_root / "core/connection.py"
spec = importlib.util.spec_from_file_location("connection_under_test", target)
connection_module = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(server_root))
try:
    with patch.dict(sys.modules, dependency_stubs()):
        spec.loader.exec_module(connection_module)
finally:
    sys.path.remove(str(server_root))


class NullLogger:
    def bind(self, **kwargs):
        return self

    def warning(self, *args, **kwargs):
        pass


class ConnectionFunctionCallTest(unittest.TestCase):
    def make_connection(self, llm):
        connection = connection_module.ConnectionHandler.__new__(
            connection_module.ConnectionHandler
        )
        connection.intent = object()
        connection.config = {
            "selected_module": {"Intent": "test_intent"},
            "Intent": {"test_intent": {"type": "function_call"}},
        }
        connection.llm = llm
        connection.logger = NullLogger()
        connection.load_function_plugin = False
        connection.func_handler = None
        connection.loop = None
        connection.dialogue = connection_module.Dialogue()
        return connection

    def test_disabled_function_call_skips_tools_and_fewshot(self):
        for value in (False, "false"):
            with self.subTest(value=value):
                connection = self.make_connection(
                    SimpleNamespace(enable_function_call=value)
                )

                with patch.object(connection_module, "UnifiedToolHandler") as handler:
                    connection._initialize_intent()
                    connection._inject_tool_call_fewshot()

                self.assertEqual(connection.intent_type, "nointent")
                self.assertFalse(connection.load_function_plugin)
                self.assertIsNone(connection.func_handler)
                self.assertEqual(connection.dialogue.dialogue, [])
                handler.assert_not_called()

    def test_function_call_remains_enabled_by_default(self):
        connection = self.make_connection(SimpleNamespace())

        with patch.object(connection_module, "UnifiedToolHandler") as handler:
            connection._initialize_intent()

        self.assertEqual(connection.intent_type, "function_call")
        self.assertTrue(connection.load_function_plugin)
        self.assertIs(connection.func_handler, handler.return_value)
        handler.assert_called_once_with(connection)


if __name__ == "__main__":
    unittest.main()
