import time
from typing import Dict, Any

from core.handle.receiveAudioHandle import handleAudioMessage, startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.utils.util import remove_punctuation_and_length

TAG = __name__

class ListenTextMessageHandler(TextMessageHandler):
    """Listen message handler"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.LISTEN

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        if "mode" in msg_json:
            conn.client_listen_mode = msg_json["mode"]
            conn.logger.bind(tag=TAG).debug(
                f"Client pickup mode:{conn.client_listen_mode}"
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
                original_text = msg_json["text"]  # Keep original text
                filtered_len, filtered_text = remove_punctuation_and_length(
                    original_text
                )

                # Identify whether it is a wake word
                is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                # Whether to enable wake word reply
                enable_greeting = conn.config.get("enable_greeting", True)

                if is_wakeup_words and not enable_greeting:
                    # If it is a wake word and wake word reply is turned off, there is no need to answer.
                    await send_stt_message(conn, original_text)
                    await send_tts_message(conn, "stop", None)
                    conn.client_is_speaking = False
                elif is_wakeup_words:
                    conn.just_woken_up = True
                    # Report pure text data (reuse the asr reporting function, but do not provide audio data)
                    enqueue_asr_report(conn, "Hey, how are you?", [])
                    await startToChat(conn, "Hey, how are you?")
                else:
                    # Report pure text data (reuse the asr reporting function, but do not provide audio data)
                    enqueue_asr_report(conn, original_text, [])
                    # Otherwise, llm is required to reply to the text content.
                    await startToChat(conn, original_text)