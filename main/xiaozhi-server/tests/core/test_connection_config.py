"""Device config errors must not start a session with public model settings."""
import asyncio
import copy
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from config import config_loader
from config.manage_api_client import DeviceBindException, DeviceNotFoundException
from core import connection


@pytest.fixture
def conn(monkeypatch):
    # Exercise the real initialization methods without loading models or hardware.
    conn = object.__new__(connection.ConnectionHandler)
    conn.read_config_from_api = True
    conn.common_config = {
        "selected_module": {"ASR": "FunASR"},
        "ASR": {"FunASR": {"type": "fun_local"}},
    }
    conn.config = copy.deepcopy(conn.common_config)
    conn.headers = {"device-id": "device", "client-id": "client"}
    conn.need_bind = False
    conn.bind_code = None
    conn.bind_completed_event = asyncio.Event()
    conn.logger = Mock()
    conn.logger.bind.return_value = conn.logger
    conn.executor = Mock()
    conn._initialize_components = Mock()
    conn.close = AsyncMock()
    monkeypatch.setattr(connection, "initialize_modules", Mock(return_value={}))
    monkeypatch.setattr(config_loader, "get_correct_words", AsyncMock(return_value=None))
    return conn


@pytest.mark.parametrize("error", [
    httpx.ReadTimeout("agent config timed out"),
    RuntimeError("API returned an error"),
])
async def test_config_failure_closes_without_starting_or_requesting_binding(conn, monkeypatch, error):
    conn.loop = asyncio.get_running_loop()
    monkeypatch.setattr(config_loader, "get_agent_models", AsyncMock(side_effect=error))

    await conn._background_initialize()

    conn.close.assert_awaited_once_with()
    conn.executor.submit.assert_not_called()
    connection.initialize_modules.assert_not_called()
    assert conn.need_bind is False
    assert not conn.bind_completed_event.is_set()
    conn.logger.info.assert_not_called()
    assert any(str(error) in call.args[0] for call in conn.logger.error.call_args_list)


@pytest.mark.parametrize("error", [
    DeviceNotFoundException("unknown device"), DeviceBindException("123456"),
])
async def test_binding_errors_keep_existing_binding_flow(conn, monkeypatch, error):
    conn.loop = asyncio.get_running_loop()
    monkeypatch.setattr(config_loader, "get_agent_models", AsyncMock(side_effect=error))

    await conn._background_initialize()

    assert conn.need_bind is True
    assert conn.bind_code == getattr(error, "bind_code", None)
    conn.executor.submit.assert_called_once_with(conn._initialize_components)
    conn.close.assert_not_awaited()
    conn.logger.info.assert_not_called()


async def test_success_applies_agent_config_before_initializing(conn, monkeypatch):
    conn.loop = asyncio.get_running_loop()
    monkeypatch.setattr(config_loader, "get_agent_models", AsyncMock(return_value={
        "selected_module": {"ASR": "DoubaoStreamASR"},
        "ASR": {"DoubaoStreamASR": {"type": "doubao_stream"}},
    }))

    await conn._background_initialize()

    assert conn.config["selected_module"]["ASR"] == "DoubaoStreamASR"
    assert conn.need_bind is False
    assert conn.bind_completed_event.is_set()
    conn.executor.submit.assert_called_once_with(conn._initialize_components)
    conn.close.assert_not_awaited()


async def test_local_config_does_not_request_agent_config(conn, monkeypatch):
    conn.read_config_from_api = False
    get_models = AsyncMock()
    monkeypatch.setattr(config_loader, "get_agent_models", get_models)

    await conn._background_initialize()

    get_models.assert_not_awaited()
    assert conn.config == conn.common_config
    assert conn.bind_completed_event.is_set()
    conn.executor.submit.assert_called_once_with(conn._initialize_components)
    conn.close.assert_not_awaited()
