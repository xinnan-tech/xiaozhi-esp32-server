"""Tests for configuration merging and device configuration failures."""
from unittest.mock import AsyncMock

import httpx
import pytest

from config import config_loader
from config.config_loader import merge_configs
from config.manage_api_client import DeviceBindException, DeviceNotFoundException


def test_merge_simple_override():
    default = {"a": 1, "b": 2}
    custom = {"b": 99}
    assert merge_configs(default, custom) == {"a": 1, "b": 99}


def test_merge_adds_new_key():
    default = {"a": 1}
    custom = {"b": 2}
    assert merge_configs(default, custom) == {"a": 1, "b": 2}


def test_merge_recursive_dict():
    default = {"x": {"a": 1, "b": 2}}
    custom = {"x": {"b": 99}}
    assert merge_configs(default, custom) == {"x": {"a": 1, "b": 99}}


def test_merge_deep_recursive():
    default = {"a": {"b": {"c": 1, "d": 2}}}
    custom = {"a": {"b": {"c": 99}}}
    assert merge_configs(default, custom) == {"a": {"b": {"c": 99, "d": 2}}}


def test_merge_replaces_non_dict_with_dict():
    default = {"a": 1}
    custom = {"a": {"nested": True}}
    assert merge_configs(default, custom) == {"a": {"nested": True}}


def test_merge_replaces_dict_with_non_dict():
    default = {"a": {"nested": True}}
    custom = {"a": 1}
    assert merge_configs(default, custom) == {"a": 1}


def test_merge_does_not_mutate_defaults():
    default = {"a": {"b": 1}}
    custom = {"a": {"c": 2}}
    merge_configs(default, custom)
    assert default == {"a": {"b": 1}}  # unchanged


@pytest.mark.parametrize("error", [
    httpx.ReadTimeout("agent config timed out"),
    httpx.ConnectError("manager API unavailable"),
    RuntimeError("API returned an error"),
    DeviceNotFoundException("unknown device"),
    DeviceBindException("123456"),
])
async def test_private_config_propagates_agent_errors(monkeypatch, error):
    monkeypatch.setattr(config_loader, "get_agent_models", AsyncMock(side_effect=error))
    monkeypatch.setattr(config_loader, "get_correct_words", AsyncMock(return_value=None))

    with pytest.raises(type(error)) as raised:
        await config_loader.get_private_config_from_api(
            {"selected_module": {"ASR": "FunASR"}}, "device", "client"
        )

    assert raised.value is error


@pytest.mark.parametrize("correct_words", [None, {"小志": "小智"}])
async def test_private_config_keeps_agent_selection(monkeypatch, correct_words):
    agent_config = {"selected_module": {"ASR": "DoubaoStreamASR"}}
    get_models = AsyncMock(return_value=agent_config)
    monkeypatch.setattr(config_loader, "get_agent_models", get_models)
    monkeypatch.setattr(config_loader, "get_correct_words", AsyncMock(return_value=correct_words))
    selected = {"ASR": "FunASR"}

    result = await config_loader.get_private_config_from_api(
        {"selected_module": selected}, "device", "client"
    )

    get_models.assert_awaited_once_with("device", "client", selected)
    assert result["selected_module"]["ASR"] == "DoubaoStreamASR"
    assert result.get("correct_words") == correct_words


async def test_private_config_tolerates_optional_correct_words_failure(monkeypatch):
    agent_config = {"selected_module": {"ASR": "DoubaoStreamASR"}}
    monkeypatch.setattr(config_loader, "get_agent_models", AsyncMock(return_value=agent_config))
    monkeypatch.setattr(config_loader, "get_correct_words", AsyncMock(side_effect=RuntimeError("unavailable")))

    result = await config_loader.get_private_config_from_api(
        {"selected_module": {}}, "device", "client"
    )

    assert result == agent_config
    assert "correct_words" not in result
