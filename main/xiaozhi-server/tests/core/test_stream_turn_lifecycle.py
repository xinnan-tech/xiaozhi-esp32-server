"""Exercise real provider callbacks with deterministic turn changes, without network/audio."""
import asyncio
import queue
import threading
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

from core.providers.tts import huoshan_double_stream as huoshan
from core.providers.tts.dto.dto import SentenceType
from core.providers.llm.openai.openai import LLMProvider
from core.handle.sendAudioHandle import sendAudioMessage, _start_background_sender


@pytest.mark.parametrize("resource_type", [False, True])
@pytest.mark.parametrize("switch_turn", [False, True])
def test_huoshan_encoding_callback_keeps_original_turn(resource_type, switch_turn):
    provider = huoshan.TTSProvider.__new__(huoshan.TTSProvider)
    conn = SimpleNamespace(sentence_id="A", client_abort=False, stop_event=threading.Event())
    provider.conn = conn
    provider.current_sentence_id = "A"
    provider.tts_audio_queue = queue.Queue()
    provider.resource_type = resource_type
    provider._sentence_text_map = {"A": "old subtitle", "B": "new subtitle"}
    provider.print_response = Mock()
    provider.ws = SimpleNamespace(recv=AsyncMock(return_value=b"pcm"), close=AsyncMock())
    provider.parser_response = lambda msg: SimpleNamespace(
        optional=SimpleNamespace(event=huoshan.EVENT_TTSResponse, sessionId="A"),
        header=SimpleNamespace(message_type=huoshan.AUDIO_ONLY_RESPONSE), payload=b"pcm",
    )

    def encode(data, callback):
        if switch_turn:
            conn.sentence_id = "B"
            provider.current_sentence_id = "B"
        callback(b"opus")
        conn.stop_event.set()

    provider.wav_to_opus_data_audio_raw_stream = encode
    asyncio.run(provider._start_monitor_tts_response())
    items = list(provider.tts_audio_queue.queue)
    audio = [item for item in items if item[0] == SentenceType.MIDDLE]
    assert audio == ([] if switch_turn else [(SentenceType.MIDDLE, b"opus", None, "A")])
    assert all(len(item) == 4 and item[3] == "A" for item in items)
    assert provider._sentence_text_map["B"] == "new subtitle"


def test_huoshan_waits_for_receiver_before_resetting_encoder():
    provider = huoshan.TTSProvider.__new__(huoshan.TTSProvider)
    provider.conn = SimpleNamespace(sentence_id="B", client_abort=False)
    provider.current_sentence_id = "A"
    provider._sentence_text_map = {"A": "old", "B": "new"}
    provider.enable_ws_reuse = True
    provider.activate_session = False
    provider._monitor_task = None
    order = []

    async def cancel(**kwargs):
        order.append("receiver stopped")

    provider._cancel_monitor_task = cancel
    provider.reset_stream_state = lambda: order.append("stream reset")
    provider.opus_encoder = SimpleNamespace(reset_state=lambda: order.append("encoder reset"))
    provider._ensure_connection = AsyncMock()
    provider.ws = object()
    provider.voice = "voice"
    provider.get_payload_bytes = Mock(return_value=b"{}")
    provider.send_event = AsyncMock()
    asyncio.run(provider.start_session("B"))
    assert order == ["receiver stopped", "stream reset", "encoder reset"]
    assert provider.current_sentence_id == "B"
    assert provider._sentence_text_map == {"B": "new"}


def test_stale_audio_and_last_do_not_send_or_close_new_turn():
    conn = SimpleNamespace(sentence_id="B", client_abort=False, close=AsyncMock())
    for kind in (SentenceType.FIRST, SentenceType.MIDDLE, SentenceType.LAST):
        asyncio.run(sendAudioMessage(conn, kind, b"opus", "old", "A"))
    conn.close.assert_not_awaited()


def test_background_sender_checks_turn_again_at_send_time():
    conn = SimpleNamespace(sentence_id="B", client_abort=False)
    controller = Mock()
    _start_background_sender(conn, controller, {"sentence_id": "A"})
    callback = controller.start_sending.call_args.args[0]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(callback(b"old opus"))


@pytest.mark.parametrize("reuse", [False, True])
def test_huoshan_receiver_cancellation_respects_connection_reuse(reuse):
    async def scenario():
        provider = huoshan.TTSProvider.__new__(huoshan.TTSProvider)
        provider.conn = SimpleNamespace(stop_event=threading.Event())
        waiting = asyncio.Event()

        async def recv():
            waiting.set()
            await asyncio.Future()

        ws = SimpleNamespace(recv=recv, close=AsyncMock())
        provider.ws = ws
        provider._monitor_task = asyncio.create_task(provider._start_monitor_tts_response())
        await waiting.wait()
        await provider._cancel_monitor_task(keep_connection=reuse)
        assert provider._monitor_task is None
        if reuse:
            assert provider.ws is ws
            ws.close.assert_not_awaited()
        else:
            assert provider.ws is None
            ws.close.assert_awaited_once()

    asyncio.run(scenario())


@pytest.mark.parametrize("functions", [False, True])
def test_openai_closes_http_stream_when_cancelled(functions):
    provider = LLMProvider.__new__(LLMProvider)
    provider.normalize_dialogue = lambda dialogue: dialogue
    provider.model_name = "fake"
    for attr in ("max_tokens", "temperature", "top_p", "frequency_penalty"):
        setattr(provider, attr, None)
    provider._apply_thinking_disabled = lambda params: None
    cancelled = False

    def chunks():
        nonlocal cancelled
        # Empty/think chunks must also check cancellation at the HTTP layer.
        cancelled = True
        yield SimpleNamespace(choices=[])
        pytest.fail("provider continued consuming cancelled stream")

    stream = Mock()
    stream.__iter__ = Mock(return_value=chunks())
    create = Mock(return_value=stream)
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    response = provider.response_with_functions if functions else provider.response
    assert list(response("session", [], cancel_check=lambda: cancelled)) == []
    stream.close.assert_called_once()
    create.reset_mock()
    assert list(response("session", [], cancel_check=lambda: True)) == []
    create.assert_not_called()
