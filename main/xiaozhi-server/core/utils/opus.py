from core.providers.tts.dto.dto import MessageTag

def pack_opus_with_header(opus_data: bytes, message_tag: MessageTag = MessageTag.NORMAL) -> bytes:
    header = bytearray(16)
    header[0] = 1 # default value is 1 for audio message
    header[1] = message_tag.value
    header[2:6] = len(opus_data).to_bytes(4, "big")
    # 3-15 bytes is reserved for future use, currently not used
    complete_packet = bytes(header) + opus_data
    return complete_packet