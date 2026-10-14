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

# edge_tts 7.3.1 在 ws 返回坏 metadata 帧（非 JSON 或非 utf-8 bytes）时，
# 父类 __parse_metadata 调 json.loads 抛 JSONDecodeError / UnicodeDecodeError；
# stream() 的音频收帧循环被中断，听不到声音。
#
# 父类 __stream 内部用编译期锁死的 mangled 名
# `self._Communicate__parse_metadata(data)` 调用，子类覆写根本走不到，所以
# 必须在父类 Communicate 类上做 monkey-patch：替换 mangled 方法为带兜底的
# wrapper，让坏帧悄悄丢掉，音频二进制帧继续往下走。连续坏帧超阈值主动
# raise NoAudioReceived 让 base.py 的 5 次重试接管。
#
# Communicate 类内 `__parse_metadata` 写法在类外访问必须用 mangled 名
# `_Communicate__parse_metadata`；直接用 `"__parse_metadata"` 字面访问永远拿不到。
_METADATA_FALLBACK_COUNT = 5
_PARSED_METADATA_ATTR = "_Communicate__parse_metadata"


def _install_metadata_patch():
    """模块级一次性 patch，import 时执行。

    三道闸门：
      1. 探测父类 mangled 方法存在；不存在则 wrapper 不写入（patch 哑火）
      2. wrapper 仅捕获 json.JSONDecodeError + UnicodeDecodeError；
         KeyError/UnknownResponse/UnexpectedResponse 等真协议错误冒泡给 base.py 重试
      3. 连续坏帧超 _METADATA_FALLBACK_COUNT 主动 raise NoAudioReceived
    """
    cls = edge_tts.communicate.Communicate
    original = cls.__dict__.get(_PARSED_METADATA_ATTR)
    if original is None:
        logger.bind(tag=TAG).error(
            f"edge-tts Communicate.{_PARSED_METADATA_ATTR} 不存在，"
            "metadata patch 失效，升级 edge_tts 后清掉这段兜底"
        )
        return

    def wrapper(self, data):
        try:
            return original(self, data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            count = self.state.get("bad_metadata_count", 0) + 1
            self.state["bad_metadata_count"] = count
            logger.bind(tag=TAG).warning(
                f"edge-tts metadata 帧非 JSON，已忽略（第 {count}/{_METADATA_FALLBACK_COUNT} 次）: {e}"
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

    setattr(cls, _PARSED_METADATA_ATTR, wrapper)
    logger.bind(tag=TAG).info(
        f"edge-tts Communicate.{_PARSED_METADATA_ATTR} patch 安装成功"
    )


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
