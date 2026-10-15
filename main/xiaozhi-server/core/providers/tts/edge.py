import json
import os
import uuid

import edge_tts
import edge_tts.communicate
from datetime import datetime

from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()

# 微软 2026-10 起对 legacy 消费者接口返回 403，edge-tts 7.3.1 仍走
# speech.platform.bing.com 走不通。临时把 WSS_URL 切到
# api.msedgeservices.com；等上游 PR rany2/edge-tts#491 合并后清掉。
_NEW_WSS_URL = (
    "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
    f"?Ocp-Apim-Subscription-Key={edge_tts.constants.TRUSTED_CLIENT_TOKEN}"
)
edge_tts.constants.WSS_URL = _NEW_WSS_URL
edge_tts.communicate.WSS_URL = _NEW_WSS_URL

# edge_tts 7.3.1 在 ws 返回坏 metadata 帧（非 JSON 或非 utf-8 bytes）时，
# 父类 __parse_metadata 调 json.loads 抛 JSONDecodeError / UnicodeDecodeError；
# stream() 收帧循环被中断，听不到声音。
#
# 父类 __stream 用编译期锁死的 mangled 名
# `self._Communicate__parse_metadata(data)` 调用，子类覆写走不到，只能在
# 父类 Communicate 类上做 monkey-patch：让坏帧悄悄丢掉，音频二进制帧继续
# 走。连续坏帧超阈值主动 raise NoAudioReceived 让 base.py 5-retry 接管。
#
# 类外访问双下划线属性必须用 mangled 名 `_Communicate__parse_metadata`。
_METADATA_FALLBACK_COUNT = 5
_PARSED_METADATA_ATTR = "_Communicate__parse_metadata"
_LAST_PARTIAL_TEXT_KEY = "_last_partial_text"


def _install_metadata_patch():
    """模块级一次性 patch。

    闸门：
      1. 父类 mangled 方法不存在 → wrapper 不写入
      2. wrapper 仅吞 JSONDecodeError / UnicodeDecodeError；
         真协议错误冒泡给 base.py 重试
      3. 连续坏帧超 _METADATA_FALLBACK_COUNT 主动 raise NoAudioReceived
      4. reload guard：再次执行时若当前类方法已是本模块 _wrapper 直接 return，
         避免 importlib.reload / uvicorn --reload 场景下 wrapper 套 wrapper
         导致 original 指向旧 wrapper，坏帧计数累加倍增
      5. partial_text 变更时 reset 计数：长文本 stream() 内分多段
         metadata 帧属正常现象，跨段不应累计
    """
    cls = edge_tts.communicate.Communicate
    current = cls.__dict__.get(_PARSED_METADATA_ATTR)
    if current is _metadata_wrapper:
        return
    if _metadata_wrapper.__wrapped__ is not None and current is _metadata_wrapper.__wrapped__:
        pass
    elif current is None:
        logger.bind(tag=TAG).error(
            "edge-tts Communicate.{} 不存在，metadata patch 失效，"
            "升级 edge_tts 后清掉这段兜底",
            _PARSED_METADATA_ATTR,
        )
        return
    _metadata_wrapper.__wrapped__ = current
    setattr(cls, _PARSED_METADATA_ATTR, _metadata_wrapper)
    logger.bind(tag=TAG).info(
        "edge-tts Communicate.{} patch 安装成功", _PARSED_METADATA_ATTR
    )


def _make_metadata_wrapper():
    """构建唯一 wrapper 闭包，__wrapped__ 字段记录被替换的原始方法。"""

    def _metadata_wrapper(self, data):
        original = _metadata_wrapper.__wrapped__
        try:
            result = original(self, data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            count = self.state.get("bad_metadata_count", 0) + 1
            self.state["bad_metadata_count"] = count
            if count == 1 or count % 5 == 0:
                logger.bind(tag=TAG).warning(
                    "edge-tts metadata 帧非 JSON，已忽略（第 {}/{} 次）: {}",
                    count, _METADATA_FALLBACK_COUNT, e,
                )
            if count > _METADATA_FALLBACK_COUNT:
                raise edge_tts.exceptions.NoAudioReceived(
                    f"edge-tts 连续 {count} 次返回非 JSON metadata 帧"
                )
            return {
                "type": "metadata_ignored",
                "offset": 0,
                "duration": 0,
                "text": "",
            }
        # 成功路径：partial_text 变更时 reset 计数，避免长文本跨段累加
        partial = result.get("text") if isinstance(result, dict) else None
        if partial is not None and self.state.get(_LAST_PARTIAL_TEXT_KEY) != partial:
            self.state[_LAST_PARTIAL_TEXT_KEY] = partial
            self.state["bad_metadata_count"] = 0
        return result

    _metadata_wrapper.__wrapped__ = None
    return _metadata_wrapper


_metadata_wrapper = _make_metadata_wrapper()


_install_metadata_patch()


class TTSProvider(TTSProviderBase):
    TTS_PARAM_CONFIG = [
        ("ttsVolume", "volume", 0, 100, 50, int),
        ("ttsRate", "speech_rate", -100, 100, 0, int),
        ("ttsPitch", "pitch_rate", -100, 100, 0, int),
    ]

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("format", "mp3")

        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        speech_rate = config.get("rate", "0")
        self.speech_rate = int(speech_rate) if speech_rate else 0

        pitch_rate = config.get("pitch", "0")
        self.pitch_rate = int(pitch_rate) if pitch_rate else 0

        self._apply_percentage_params(config)

        self.edge_rate = f"{self.speech_rate:+}%"
        self.edge_volume = f"{self.volume:+}%"
        self.edge_pitch = f"{self.pitch_rate:+}Hz"

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        communicate = edge_tts.communicate.Communicate(
            text,
            voice=self.voice,
            rate=self.edge_rate,
            volume=self.edge_volume,
            pitch=self.edge_pitch,
        )
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as f:
                pass

            with open(output_file, "ab") as f:
                async for chunk in communicate.stream():
                    if chunk.get("type") == "audio":
                        f.write(chunk["data"])
        else:
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio_bytes += chunk["data"]
            return audio_bytes
        return None
