"""
Report features:
1. Each connection has its own report queue and processing thread
2. Report thread lifecycle bound to connection object
3. Use ConnectionHandler.enqueue_tts_report method for reporting

See core/connection.py for implementation details.
"""

import time
import base64
from typing import List, Dict, Any
from config.live_agent_api_client import report_chat_message
from core.providers.tts.dto.dto import MessageTag
from core.utils.textUtils import strip_emotion_tags

TAG = __name__


def report(conn, role, text: str, opus_data: List[bytes] | None = None, report_time: int = 0, attachments: List[Dict[str, Any]] | None = None):
    """Execute chat message report to live-agent-api
    
    Args:
        conn: Connection object
        role: Message role, 1=user, 2=agent
        text: Message text content
        opus_data: Opus audio data (list of opus packets)
        report_time: Unix timestamp when message actually occurred (for correct ordering)
        attachments: Optional list of attachments (multimodal content), format:
            [
                {"type": "image", "url": "https://..."},
                {"type": "file", "url": "https://..."}
            ]
    """
    try:
        # Build content items for new API format
        content_items = []
        
        # Add text content if exists
        if text:
            content_items.append({
                "message_type": "text",
                "message_content": text
            })
        
        # Add audio content if exists (convert opus packets to base64)
        if opus_data:
            # Concatenate all opus packets
            opus_bytes = b"".join(opus_data)
            # Convert to base64
            audio_base64 = base64.b64encode(opus_bytes).decode("utf-8")
            content_items.append({
                "message_type": "audio",
                "message_content": audio_base64
            })
        
        # Add attachments if exists (images and files)
        if attachments:
            for attachment in attachments:
                att_type = attachment.get("type")
                url = attachment.get("url")
                if att_type and url:
                    content_items.append({
                        "message_type": att_type,  # "image" or "file"
                        "message_content": url
                    })
        
        # Skip if no content to report
        if not content_items:
            conn.logger.bind(tag=TAG).warning("No content to report, skipping")
            return
        
        # Report to live-agent-api with message_time for correct ordering
        report_chat_message(
            agent_id=conn.agent_id,
            role=role,
            content_items=content_items,
            message_time=report_time if report_time > 0 else None
        )
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Chat message report failed: {e}")


def enqueue_tts_report(conn, text, opus_data, message_tag=MessageTag.NORMAL, report_time=None):
    """Enqueue TTS data for reporting (Agent message)
    
    Args:
        conn: Connection object
        text: Synthesized text (may contain emotion tags)
        opus_data: Opus audio data (list of opus packets)
        message_tag: Message tag for special messages (opening/closing)
        report_time: Timestamp when message actually occurred (for correct ordering)
    """
    # Check if reporting is enabled for live-agent-api mode
    if not conn.read_config_from_live_agent_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    # if the message is opening and the connection is reconnected, skip the report
    if message_tag == MessageTag.OPENING and conn.reconnected:
        conn.logger.bind(tag=TAG).info(f"Opening message is reconnected, skipping report")
        return 
    
    # Use provided report_time or current time
    timestamp = report_time if report_time is not None else int(time.time())
    
    try:
        # Remove emotion tags from text before reporting
        clean_text = strip_emotion_tags(text)
        
        # Use connection's queue, pass text and binary data
        if conn.chat_history_conf == 2:
            # Report with audio (TTS never has attachments)
            conn.report_queue.put((2, clean_text, opus_data, timestamp, None))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data enqueued: agent_id={conn.agent_id}, audio packets: {len(opus_data)}, report_time: {timestamp}"
            )
        else:
            # Report without audio (text only)
            conn.report_queue.put((2, clean_text, None, timestamp, None))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data enqueued: agent_id={conn.agent_id}, no audio, report_time: {timestamp}"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to enqueue TTS report: {text}, {e}")


def enqueue_asr_report(conn, text, opus_data, attachments=None, report_time=None):
    """Enqueue ASR data for reporting (User message)
    
    Args:
        conn: Connection object
        text: Recognized text
        opus_data: Opus audio data (list of opus packets)
        attachments: Optional list of attachments (images, files)
        report_time: Timestamp when message actually occurred (for correct ordering)
    """
    # Check if reporting is enabled for live-agent-api mode
    if not conn.read_config_from_live_agent_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    
    # Use provided report_time or current time
    timestamp = report_time if report_time is not None else int(time.time())
    
    try:
        # Use connection's queue, pass text, audio data, and attachments
        # Queue format: (role, text, opus_data, timestamp, attachments)
        if conn.chat_history_conf == 2:
            # Report with audio
            conn.report_queue.put((1, text, opus_data, timestamp, attachments))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data enqueued: agent_id={conn.agent_id}, audio packets: {len(opus_data)}, attachments: {len(attachments) if attachments else 0}, report_time: {timestamp}"
            )
        else:
            # Report without audio (text only, but may have attachments)
            conn.report_queue.put((1, text, None, timestamp, attachments))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data enqueued: agent_id={conn.agent_id}, no audio, attachments: {len(attachments) if attachments else 0}, report_time: {timestamp}"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).debug(f"Failed to enqueue ASR report: {text}, {e}")
