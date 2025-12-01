from typing import Dict, Any

from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.utils.dialogue import Message

TAG = __name__


class AttachmentTextMessageHandler(TextMessageHandler):
    """Attachment Message Handler - process image and file attachments"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.ATTACHMENT

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        """
        Process attachment message and store it in dialogue
        
        消息格式:
        {
            "type": "attachment",
            "attachment_type": "image" | "file",
            "url": "https://..."
        }
        """
        attachment_type = msg_json.get("attachment_type")  # "image" or "file"
        url = msg_json.get("url")
        
        if not attachment_type or not url:
            conn.logger.bind(tag=TAG).warning(
                f"Invalid attachment message: missing attachment_type or url"
            )
            return
        
        # Build multimodal content format (OpenAI compatible)
        if attachment_type == "image":
            content = [
                {
                    "type": "input_image",
                    "image_url": url
                }
            ]
        elif attachment_type == "file":
            # File type: store as custom format, LLM layer needs special handling
            content = [
                {
                    "type": "input_file",
                    "file_url": url
                }
            ]
        
        # Store directly in dialogue
        conn.dialogue.put(Message(role="user", content=content))
        
        conn.logger.bind(tag=TAG).info(
            f"Attachment stored in dialogue: type={attachment_type}, url={url}"
        )

