"""Regression tests for null JSON-RPC ``id`` handling in the device MCP handler.

JSON-RPC permits ``id`` to be ``null``. Before the fix, ``int(payload.get("id", 0))``
only defaulted when the key was *absent*; a present ``"id": null`` reached
``int(None)`` and raised ``TypeError``, aborting the MCP handshake and leaving the
session with ``ready=False``. These tests assert the handler tolerates a null id.

Self-contained: no conftest required.
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.providers.tools.device_mcp.mcp_handler import (  # noqa: E402
    MCPClient,
    handle_mcp_message,
)


class _DummyConn:
    """Minimal stand-in; the null-id code paths below never touch the connection."""


def test_result_payload_with_null_id_does_not_raise():
    client = MCPClient()
    # Regression: a result payload whose id is JSON null must not crash.
    asyncio.run(handle_mcp_message(_DummyConn(), client, {"result": {}, "id": None}))


def test_error_payload_with_null_id_does_not_raise():
    client = MCPClient()
    # The error branch parses the id the same way and must also tolerate null.
    asyncio.run(
        handle_mcp_message(_DummyConn(), client, {"error": {"message": "boom"}, "id": None})
    )


def test_missing_id_still_defaults_to_zero():
    client = MCPClient()
    # The original missing-key behaviour must be preserved.
    asyncio.run(handle_mcp_message(_DummyConn(), client, {"result": {}}))
