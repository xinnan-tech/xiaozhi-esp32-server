import asyncio
import queue
import threading

from core.connection import ConnectionHandler


class _Logger:
    def bind(self, **kwargs):
        return self

    def info(self, *a, **k):
        pass

    warning = error = debug = info


def _bare_handler():
    h = ConnectionHandler.__new__(ConnectionHandler)  # 跳过 __init__ 的重资源初始化
    h.logger = _Logger()
    h.stop_event = threading.Event()
    h.timeout_task = None
    h._background_init_task = None
    h._close_started = False
    h.tts = None
    h.asr = None
    h.executor = None
    h.report_thread = None
    h.report_queue = queue.Queue()
    h.asr_audio = []
    h.asr_audio_queue = queue.Queue()
    h.websocket = object()
    return h


def test_close_is_idempotent():
    h = _bare_handler()

    async def run():
        await h.close()
        assert h._close_started is True
        assert h.websocket is None
        await h.close()  # 第二次应直接返回，不再重复释放

    asyncio.run(run())


def test_close_drains_asr_buffers():
    h = _bare_handler()
    h.asr_audio.extend([b"a", b"b"])
    h.asr_audio_queue.put(b"x")

    async def run():
        await h.close()

    asyncio.run(run())
    assert h.asr_audio == []
    assert h.asr_audio_queue.empty()
