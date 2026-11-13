"""流式 TTS 的重试：失败要真的重试，日志也不能把失败写成成功。

index_stream / minimax_httpstream 原来的 to_tts_single_stream 只试一次；
失败后 max_repeat_time 只减 1（5→4），于是 `if max_repeat_time > 0` 恒为真，
失败也照样打「语音生成成功」，真正的「语音生成失败」分支永远走不到。
"""
import queue
from contextlib import contextmanager

import pytest
from loguru import logger

from core.providers.tts import index_stream, minimax_httpstream
from core.providers.tts.dto.dto import SentenceType

PROVIDERS = [index_stream.TTSProvider, minimax_httpstream.TTSProvider]

# 日志里区分成功/失败的固定文案
SUCCESS_LOG = "语音生成成功"
FAILURE_LOG = "请检查网络或服务是否正常"


def _make_provider(cls):
    """只填 to_tts_single_stream 用得到的字段。

    绕开 __init__：它会去建 opus 编码器，而编解码依赖系统里的 libopus，
    单测里根本用不上。
    """
    provider = object.__new__(cls)
    provider.tts_audio_queue = queue.Queue()
    provider.correct_words = {}
    provider._correct_words_pattern = None
    provider._tts_first_sent = False
    return provider


@contextmanager
def _capture_logs():
    """抓 loguru 的输出。"""
    messages = []
    handler_id = logger.add(
        lambda msg: messages.append(str(msg)), level="DEBUG", format="{message}"
    )
    try:
        yield messages
    finally:
        logger.remove(handler_id)


def _drain(provider):
    items = []
    while not provider.tts_audio_queue.empty():
        items.append(provider.tts_audio_queue.get())
    return items


def _stub(provider, results):
    """把 text_to_speak 换成按 results 依次返回的桩，并记录调用次数。

    results 里的每一项要么是 (ok, audio_sent)，要么是 Exception（直接抛出）。
    """
    calls = []

    async def fake_text_to_speak(text, is_last):
        calls.append(text)
        result = results[min(len(calls) - 1, len(results) - 1)]
        if isinstance(result, Exception):
            raise result
        return result

    provider.text_to_speak = fake_text_to_speak
    return calls


@pytest.mark.parametrize("cls", PROVIDERS)
def test_transient_failure_is_retried(cls):
    """前两次失败、第三次成功：必须真的重试到成功。"""
    provider = _make_provider(cls)
    calls = _stub(provider, [(False, False), (False, False), (True, True)])

    with _capture_logs() as messages:
        provider.to_tts_single_stream("今天天气怎么样")

    assert len(calls) == 3, "失败后应该重试，而不是只试一次"
    assert any(SUCCESS_LOG in m for m in messages), "重试成功后应该打「语音生成成功」"
    assert not any(FAILURE_LOG in m for m in messages), "最终成功了不该再打「语音生成失败」"


@pytest.mark.parametrize("cls", PROVIDERS)
def test_failure_is_logged_as_failure(cls):
    """一直失败：日志必须是失败，不能反着写成成功。"""
    provider = _make_provider(cls)
    calls = _stub(provider, [(False, False)])

    with _capture_logs() as messages:
        provider.to_tts_single_stream("今天天气怎么样")

    assert len(calls) == 5, "最多重试 5 次"
    assert any(FAILURE_LOG in m for m in messages), "失败必须打「语音生成失败」"
    assert not any(SUCCESS_LOG in m for m in messages), "失败不能打「语音生成成功」"


@pytest.mark.parametrize("cls", PROVIDERS)
def test_exception_is_retried_and_logged_as_failure(cls):
    """text_to_speak 抛异常时同样要重试，并且按失败记账。"""
    provider = _make_provider(cls)
    calls = _stub(provider, [RuntimeError("连接超时")])

    with _capture_logs() as messages:
        provider.to_tts_single_stream("今天天气怎么样")

    assert len(calls) == 5
    assert any(FAILURE_LOG in m for m in messages)
    assert not any(SUCCESS_LOG in m for m in messages)


@pytest.mark.parametrize("cls", PROVIDERS)
def test_no_retry_once_audio_was_pushed(cls):
    """音频已经推给设备就不能再试，否则同一句会被播两遍。"""
    provider = _make_provider(cls)
    calls = _stub(provider, [(False, True)])

    with _capture_logs() as messages:
        provider.to_tts_single_stream("今天天气怎么样")

    assert len(calls) == 1, "音频已经推出去就不该重试"
    assert any(FAILURE_LOG in m for m in messages)


@pytest.mark.parametrize("cls", PROVIDERS)
def test_last_marker_sent_once_after_retries_exhausted(cls):
    """失败收尾的 LAST 标记只发一次，不能每次重试都发。"""
    provider = _make_provider(cls)
    _stub(provider, [(False, False)])

    provider.to_tts_single_stream("今天天气怎么样")

    items = _drain(provider)
    lasts = [i for i in items if i[0] is SentenceType.LAST]
    assert len(lasts) == 1, f"LAST 标记应该只发一次，实际 {len(lasts)} 次"


@pytest.mark.parametrize("cls", PROVIDERS)
def test_no_last_marker_when_retry_succeeds(cls):
    """重试成功时不能发 LAST，否则成功的音频会排在 LAST 后面听不到。"""
    provider = _make_provider(cls)
    _stub(provider, [(False, False), (True, True)])

    provider.to_tts_single_stream("今天天气怎么样")

    items = _drain(provider)
    assert not [i for i in items if i[0] is SentenceType.LAST]
