"""
Report features:
1. Each connection has its own report queue and processing thread
2. Report thread lifecycle bound to connection object
3. Use ConnectionHandler.enqueue_tts_report method for reporting

See core/connection.py for implementation details.
"""

import re
import time
import base64

from config.live_agent_api_client import report_chat_message

TAG = __name__

# Regex pattern to match emotion tags anywhere in text
# Format: (emotion) e.g., "(happy)", "(sincere)", "(curious)"
# Matches: optional whitespace + (word) + optional whitespace
EMOTION_TAG_PATTERN = re.compile(r'\s*\([a-zA-Z_]+\)\s*')


def strip_emotion_tags(text: str) -> str:
    """
    Remove all emotion tags from TTS text.
    
    Emotion tags are in format: (emotion) typically at the start of sentences.
    Examples:
        "(happy) Hello!" -> "Hello!"
        "(sincere) That's great. (curious) What next?" -> "That's great. What next?"
        "Hello (happy) world" -> "Hello world"
    
    Args:
        text: Text with potential emotion tags
        
    Returns:
        Text with all emotion tags removed
    """
    if not text:
        return text
    
    # Remove all emotion tags from the text
    result = EMOTION_TAG_PATTERN.sub(' ', text)
    # Clean up multiple spaces and trim
    result = re.sub(r'\s+', ' ', result)
    return result.strip()


def report(conn, role, text, opus_data, report_time):
    """Execute chat message report to live-agent-api
    
    Args:
        conn: Connection object
        role: Message role, 1=user, 2=agent
        text: Message text content
        opus_data: Opus audio data (list of opus packets)
        report_time: Report timestamp (currently unused, kept for compatibility)
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
        
        # Skip if no content to report
        if not content_items:
            conn.logger.bind(tag=TAG).warning("No content to report, skipping")
            return
        
        # Report to live-agent-api (client already initialized at startup)
        report_chat_message(
            agent_id=conn.agent_id,
            role=role,
            content_items=content_items
        )
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Chat message report failed: {e}")


def enqueue_tts_report(conn, text, opus_data):
    """Enqueue TTS data for reporting (Agent message)
    
    Args:
        conn: Connection object
        text: Synthesized text (may contain emotion tags)
        opus_data: Opus audio data (list of opus packets)
    """
    # Check if reporting is enabled for live-agent-api mode
    if not conn.read_config_from_live_agent_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    
    try:
        # Remove emotion tags from text before reporting
        clean_text = strip_emotion_tags(text)
        
        # Use connection's queue, pass text and binary data
        if conn.chat_history_conf == 2:
            # Report with audio
            conn.report_queue.put((2, clean_text, opus_data, int(time.time())))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data enqueued: agent_id={conn.agent_id}, audio packets: {len(opus_data)}"
            )
        else:
            # Report without audio (text only)
            conn.report_queue.put((2, clean_text, None, int(time.time())))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data enqueued: agent_id={conn.agent_id}, no audio"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to enqueue TTS report: {text}, {e}")


def enqueue_asr_report(conn, text, opus_data):
    """Enqueue ASR data for reporting (User message)
    
    Args:
        conn: Connection object
        text: Recognized text
        opus_data: Opus audio data (list of opus packets)
    """
    # Check if reporting is enabled for live-agent-api mode
    if not conn.read_config_from_live_agent_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    
    try:
        # Use connection's queue, pass text and binary data
        if conn.chat_history_conf == 2:
            # Report with audio
            conn.report_queue.put((1, text, opus_data, int(time.time())))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data enqueued: agent_id={conn.agent_id}, audio packets: {len(opus_data)}"
            )
        else:
            # Report without audio (text only)
            conn.report_queue.put((1, text, None, int(time.time())))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data enqueued: agent_id={conn.agent_id}, no audio"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).debug(f"Failed to enqueue ASR report: {text}, {e}")
