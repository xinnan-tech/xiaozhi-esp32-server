import time
from typing import Dict, Any, List

from core.handle.receiveAudioHandle import handleAudioMessage, startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.utils.util import remove_punctuation_and_length

TAG = __name__


def build_multimodal_content(text: str, attachments: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Build multimodal content (Groq/OpenAI Responses API format)
    
    Args:
        text: Text content
        attachments: Attachments list, format:
            [
                {"type": "image", "url": "https://..."},
                {"type": "file", "url": "https://..."}
            ]
    
    Returns:
        Responses API compatible multimodal content:
        [
            {"type": "input_text", "text": "..."},
            {"type": "input_image", "image_url": "https://..."},
            {"type": "input_file", "file_url": "https://..."}
        ]
    """
    content = []
    
    # add attachments(images first, let LLM "see" them first)
    for attachment in attachments:
        att_type = attachment.get("type")
        url = attachment.get("url")
        
        if not att_type or not url:
            continue
            
        if att_type == "image":
            content.append({
                "type": "input_image",
                "image_url": url
            })
        elif att_type == "file":
            content.append({
                "type": "input_file",
                "file_url": url
            })
    
    # add text content at last
    if text:
        content.append({"type": "input_text", "text": text})
    
    return content

class ListenTextMessageHandler(TextMessageHandler):
    """Listen消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.LISTEN

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        if "mode" in msg_json:
            conn.client_listen_mode = msg_json["mode"]
            conn.logger.bind(tag=TAG).info(
                f"客户端拾音模式：{conn.client_listen_mode}"
            )
        if msg_json["state"] == "start":
            conn.client_have_voice = True
            conn.client_voice_stop = False
        elif msg_json["state"] == "stop":
            conn.client_have_voice = True
            conn.client_voice_stop = True
            if len(conn.asr_audio) > 0:
                await handleAudioMessage(conn, b"")
        elif msg_json["state"] == "detect":
            conn.client_have_voice = False
            conn.asr_audio.clear()
            if "text" in msg_json:
                conn.last_activity_time = time.time() * 1000
                original_text = msg_json["text"]  # 保留原始文本
                filtered_len, filtered_text = remove_punctuation_and_length(
                    original_text
                )

                # 识别是否是唤醒词
                is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                # 是否开启唤醒词回复
                enable_greeting = conn.config.get("enable_greeting", True)

                if is_wakeup_words and not enable_greeting:
                    # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                    await send_stt_message(conn, original_text)
                    await send_tts_message(conn, "stop", None)
                    conn.client_is_speaking = False
                elif is_wakeup_words:
                    conn.just_woken_up = True
                    # Record timestamp for correct message ordering
                    report_time = int(time.time())
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    enqueue_asr_report(conn, "嘿，你好呀", [], report_time=report_time)
                    await startToChat(conn, "嘿，你好呀")
                else:
                    # check if there are attachments(eg. images, files) in text mode
                    attachments = msg_json.get("attachments", [])
                    # Record timestamp for correct message ordering
                    report_time = int(time.time())
                    
                    if attachments:
                        # build multimodal content
                        multimodal_content = build_multimodal_content(original_text, attachments)
                        # report text data with attachments
                        enqueue_asr_report(conn, original_text, [], attachments, report_time=report_time)
                        # use multimodal content to chat
                        await startToChat(conn, original_text, multimodal_content)
                    else:
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, original_text, [], report_time=report_time)
                        # 否则需要LLM对文字内容进行答复
                        await startToChat(conn, original_text)