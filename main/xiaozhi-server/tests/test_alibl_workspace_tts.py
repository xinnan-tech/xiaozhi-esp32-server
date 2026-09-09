import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.alibl_endpoint import (
    DEFAULT_WS_URL,
    build_ws_connect_options,
    resolve_ws_url,
)
from core.utils.alibl_event import extract_sentence_start_text


class AliBLStreamEventTests(unittest.TestCase):
    def test_sentence_begin_returns_original_text(self):
        event = {
            "payload": {
                "output": {
                    "type": "sentence-begin",
                    "original_text": "第一句。",
                }
            }
        }
        self.assertEqual(extract_sentence_start_text(event), "第一句。")

    def test_non_begin_events_do_not_return_subtitles(self):
        for event_type in ("sentence-synthesis", "sentence-end"):
            event = {
                "payload": {
                    "output": {
                        "type": event_type,
                        "original_text": "第一句。",
                    }
                }
            }
            self.assertIsNone(extract_sentence_start_text(event))

    def test_empty_sentence_text_is_ignored(self):
        event = {
            "payload": {
                "output": {"type": "sentence-begin", "original_text": "  "}
            }
        }
        self.assertIsNone(extract_sentence_start_text(event))


class AliBLWorkspaceEndpointTests(unittest.TestCase):
    def test_connection_uses_happy_eyeballs(self):
        self.assertEqual(
            build_ws_connect_options(15),
            {
                "open_timeout": 15,
                "happy_eyeballs_delay": 0.25,
                "interleave": 1,
            },
        )

    def test_default_endpoint_remains_backward_compatible(self):
        self.assertEqual(resolve_ws_url(None), DEFAULT_WS_URL)

    def test_beijing_workspace_endpoint_is_supported(self):
        endpoint = (
            "wss://ws-123.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
        )
        self.assertEqual(resolve_ws_url(endpoint), endpoint)

    def test_singapore_workspace_endpoint_is_supported(self):
        endpoint = (
            "wss://ws-123.ap-southeast-1.maas.aliyuncs.com/api-ws/v1/inference"
        )
        self.assertEqual(resolve_ws_url(endpoint), endpoint)

    def test_non_alibaba_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_ws_url("wss://example.com/api-ws/v1/inference")

    def test_insecure_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_ws_url(
                "ws://ws-123.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
            )

    def test_unresolved_workspace_placeholder_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_ws_url(
                "wss://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
            )


if __name__ == "__main__":
    unittest.main()
