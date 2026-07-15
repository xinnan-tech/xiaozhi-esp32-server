from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType

TAG = __name__


def resolve_speaker_name(proxy):
    """从外部 speaker 帧解析出注入 LLM 的 speaker_name。

    Args:
        proxy: lebot 上报的 speaker 帧 {name, relationship, ...},或 None(未识别/超时)

    Returns:
        - "name(relationship)":有 name 且有 relationship
        - "name":有 name 无 relationship
        - "未知说话人":无 name(短语音未识别 / 等待超时)
    """
    if proxy and proxy.get("name"):
        name = proxy["name"]
        relationship = proxy.get("relationship")
        if relationship:
            return f"{name}({relationship})"
        return name
    return "未知说话人"


class SpeakerTextMessageHandler(TextMessageHandler):
    """外部声纹代理(如 lebot)上报的 speaker 识别结果。

    lebot 在 WS 代理路径上识别出说话人后,通过普通 JSON 文本帧上报:
        {"type": "speaker", "name": "张三", "relationship": "爸爸", ...}
    本 handler 仅负责把整帧存入 conn.proxy_speaker 并唤醒等待方,
    真正取用发生在 asr/base.py 的 handle_voice_stop。
    """

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.SPEAKER

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        conn.proxy_speaker = msg_json
        conn.proxy_speaker_ready.set()
