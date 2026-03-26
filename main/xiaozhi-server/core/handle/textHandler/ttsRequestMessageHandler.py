import json
import base64
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType

TAG = __name__


class TtsRequestMessageHandler(TextMessageHandler):
    """TTS请求消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.TTS_REQUEST

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        text = msg_json.get("text", "")
        if not text:
            conn.logger.bind(tag=TAG).warning("收到空的TTS请求")
            return

        conn.logger.bind(tag=TAG).info(f"收到TTS请求: {text[:50]}...")

        try:
            # 调用TTS provider生成音频
            audio_datas = conn.tts.to_tts(text)
            if not audio_datas:
                conn.logger.bind(tag=TAG).error("TTS生成音频失败")
                return

            # 发送开始状态
            start_response = {
                "type": "tts_response",
                "state": "start",
                "text": text
            }
            await conn.websocket.send(json.dumps(start_response))

            # 分片发送音频数据
            for i, audio_chunk in enumerate(audio_datas):
                audio_base64 = base64.b64encode(audio_chunk).decode("utf-8")
                chunk_response = {
                    "type": "tts_response",
                    "state": "sentence_start" if i == 0 else "middle",
                    "audio": audio_base64,
                    "text": text
                }
                await conn.websocket.send(json.dumps(chunk_response))

            # 发送结束状态
            stop_response = {
                "type": "tts_response",
                "state": "stop",
                "text": text
            }
            await conn.websocket.send(json.dumps(stop_response))
            conn.logger.bind(tag=TAG).info(f"发送TTS响应完成: {len(audio_datas)} 包")

        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"处理TTS请求失败: {e}")