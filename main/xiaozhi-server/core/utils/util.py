import re
import os
import json
import copy
import wave
import socket
import asyncio
import requests
import subprocess
import numpy as np
import opuslib_next
from io import BytesIO
from core.utils import p3
from pydub import AudioSegment
from typing import Callable, Any

TAG = __name__


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to Google's DNS servers
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return "127.0.0.1"


def is_private_ip(ip_addr):
    """
    Check if an IP address is a private IP address (compatible with IPv4 and IPv6).

    @param {string} ip_addr - The IP address to check.
    @return {bool} True if the IP address is private, False otherwise.
    """
    try:
        # Validate IPv4 or IPv6 address format
        if not re.match(
            r"^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$", ip_addr
        ):
            return False  # Invalid IP address format

        # IPv4 private address ranges
        if "." in ip_addr:  # IPv4 address
            ip_parts = list(map(int, ip_addr.split(".")))
            if ip_parts[0] == 10:
                return True  # 10.0.0.0/8 range
            elif ip_parts[0] == 172 and 16 <= ip_parts[1] <= 31:
                return True  # 172.16.0.0/12 range
            elif ip_parts[0] == 192 and ip_parts[1] == 168:
                return True  # 192.168.0.0/16 range
            elif ip_addr == "127.0.0.1":
                return True  # Loopback address
            elif ip_parts[0] == 169 and ip_parts[1] == 254:
                return True  # Link-local address 169.254.0.0/16
            else:
                return False  # Not a private IPv4 address
        else:  # IPv6 address
            ip_addr = ip_addr.lower()
            if ip_addr.startswith("fc00:") or ip_addr.startswith("fd00:"):
                return True  # Unique Local Addresses (FC00::/7)
            elif ip_addr == "::1":
                return True  # Loopback address
            elif ip_addr.startswith("fe80:"):
                return True  # Link-local unicast addresses (FE80::/10)
            else:
                return False  # Not a private IPv6 address

    except (ValueError, IndexError):
        return False  # IP address format error or insufficient segments


def get_ip_info(ip_addr, logger):
    try:
        # Import the shared cache manager.
        from core.utils.cache.manager import cache_manager, CacheType

        # Check the cache first.
        cached_ip_info = cache_manager.get(CacheType.IP_INFO, ip_addr)
        if cached_ip_info is not None:
            return cached_ip_info

        # Cache miss: resolve the IP through the API.
        if is_private_ip(ip_addr):
            ip_addr = ""
        # ip-api.com returns English place names worldwide; status=="fail"
        # (e.g. private/loopback addresses) yields an empty city.
        url = f"http://ip-api.com/json/{ip_addr}?fields=status,city&lang=en"
        resp = requests.get(url, timeout=5).json()
        city = resp.get("city") if resp.get("status") == "success" else None
        ip_info = {"city": city or ""}

        # Store the result in cache.
        cache_manager.set(CacheType.IP_INFO, ip_addr, ip_info)
        return ip_info
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting client ip info: {e}")
        return {}


def write_json_file(file_path, data):
    """Write data to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def remove_punctuation_and_length(text):
    # Full-width and half-width punctuation ranges.
    full_width_punctuations = (
        "！＂＃＄％＆＇（）＊＋，－。／：；＜＝＞？＠［＼］＾＿｀｛｜｝～"
    )
    half_width_punctuations = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    space = " "  # ASCII space
    full_width_space = "　"  # Full-width space

    # Remove punctuation and spaces.
    result = "".join(
        [
            char
            for char in text
            if char not in full_width_punctuations
            and char not in half_width_punctuations
            and char not in space
            and char not in full_width_space
        ]
    )

    if result == "Yeah":
        return 0, ""
    return len(result), result


def check_model_key(modelType, modelKey):
    legacy_placeholder = "\u4f60"
    if legacy_placeholder in str(modelKey) or "your" in str(modelKey).lower():
        return f"Configuration error: the API key for {modelType} is not set. Current value: {modelKey}"
    return None


def parse_string_to_list(value, separator=";"):
    """
    Convert the input value into a list.

    Args:
        value: Input value. Can be `None`, a string, or a list.
        separator: Delimiter, defaults to a semicolon.

    Returns:
        list: Normalized list result.
    """
    if value is None or value == "":
        return []
    elif isinstance(value, str):
        return [item.strip() for item in value.split(separator) if item.strip()]
    elif isinstance(value, list):
        return value
    return []


def check_ffmpeg_installed() -> bool:
    """
    Check whether `ffmpeg` is correctly installed and executable.

    Returns:
        bool: `True` when ffmpeg is available; otherwise raises `ValueError`.

    Raises:
        ValueError: Raised when ffmpeg is missing or a required dependency is unavailable.
    """
    try:
        # Try running the ffmpeg command.
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # Non-zero exit codes raise CalledProcessError.
        )

        output = (result.stdout + result.stderr).lower()
        if "ffmpeg version" in output:
            return True

        # Missing version output is treated as an error as well.
        raise ValueError("No valid ffmpeg version output was detected.")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Extract stderr details.
        stderr_output = ""
        if isinstance(e, subprocess.CalledProcessError):
            stderr_output = (e.stderr or "").strip()
        else:
            stderr_output = str(e).strip()

        # Build the base error message.
        error_msg = [
            "ffmpeg could not be started correctly.\n",
            "Recommended next steps:",
            "1. Make sure the correct conda environment is activated.",
            "2. Check the project installation docs for ffmpeg setup inside that conda environment.\n",
        ]

        # Add more targeted guidance when we can identify the cause.
        if "libiconv.so.2" in stderr_output:
            error_msg.append("Missing dependency detected: libiconv.so.2")
            error_msg.append("Suggested fix in the current conda environment:")
            error_msg.append("   conda install -c conda-forge libiconv\n")
        elif (
            "no such file or directory" in stderr_output
            and "ffmpeg" in stderr_output.lower()
        ):
            error_msg.append("The system could not find the ffmpeg executable.")
            error_msg.append("Suggested fix in the current conda environment:")
            error_msg.append("   conda install -c conda-forge ffmpeg\n")
        else:
            error_msg.append("Error details:")
            error_msg.append(stderr_output or "Unknown error.")

        # Raise a detailed exception message.
        raise ValueError("\n".join(error_msg)) from e


def extract_json_from_string(input_string):
    """Extract the JSON portion from a string."""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string, re.DOTALL)
    if match:
        return match.group(1)
    return None


def audio_to_data_stream(
    audio_file_path, is_opus=True, callback: Callable[[Any], Any] = None, sample_rate=16000, opus_encoder=None
) -> None:
    # Get the file extension.
    file_type = os.path.splitext(audio_file_path)[1]
    if file_type:
        file_type = file_type.lstrip(".")
    # Read the audio file. `-nostdin` prevents FFmpeg from blocking on stdin.
    audio = AudioSegment.from_file(
        audio_file_path, format=file_type, parameters=["-nostdin"]
    )

    # Convert to mono, target sample rate, and 16-bit little-endian PCM.
    audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)

    # Extract raw PCM data.
    raw_data = audio.raw_data
    pcm_to_data_stream(raw_data, is_opus, callback, sample_rate, opus_encoder)


async def audio_to_data(
    audio_file_path: str, is_opus: bool = True, use_cache: bool = True
) -> list[bytes]:
    """
    Convert an audio file into a list of Opus or PCM frames.

    Args:
        audio_file_path: Audio file path.
        is_opus: Whether to encode as Opus.
        use_cache: Whether to use the audio cache.
    """
    from core.utils.cache.manager import cache_manager
    from core.utils.cache.config import CacheType

    # Build the cache key from the file path and encoding type.
    cache_key = f"{audio_file_path}:{is_opus}"

    # Try the cache first.
    if use_cache:
        cached_result = cache_manager.get(CacheType.AUDIO_DATA, cache_key)
        if cached_result is not None:
            return cached_result

    def _sync_audio_to_data():
        # Read the file extension.
        file_type = os.path.splitext(audio_file_path)[1]
        if file_type:
            file_type = file_type.lstrip(".")
        # Read the audio file. `-nostdin` prevents FFmpeg from blocking on stdin.
        audio = AudioSegment.from_file(
            audio_file_path, format=file_type, parameters=["-nostdin"]
        )

        # Convert to mono, 16 kHz, 16-bit little-endian PCM.
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

        # Extract raw PCM data.
        raw_data = audio.raw_data

        # Initialize the Opus encoder.
        encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)

        # Encoding parameters.
        frame_duration = 60  # 60ms per frame
        frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

        datas = []
        # Process every frame, padding the final frame if needed.
        for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
            # Read the current frame bytes.
            chunk = raw_data[i : i + frame_size * 2]

            # Pad the last frame with zeros if needed.
            if len(chunk) < frame_size * 2:
                chunk += b"\x00" * (frame_size * 2 - len(chunk))

            if is_opus:
                # Convert to a numpy array before Opus encoding.
                np_frame = np.frombuffer(chunk, dtype=np.int16)
                # Encode the Opus frame.
                frame_data = encoder.encode(np_frame.tobytes(), frame_size)
            else:
                frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)

            datas.append(frame_data)

        return datas

    loop = asyncio.get_running_loop()
    # Run the synchronous audio conversion in a worker thread.
    result = await loop.run_in_executor(None, _sync_audio_to_data)

    # Cache the result with the configured TTL.
    if use_cache:
        cache_manager.set(CacheType.AUDIO_DATA, cache_key, result)

    return result


def audio_bytes_to_data_stream(
    audio_bytes, file_type, is_opus, callback: Callable[[Any], Any], sample_rate=16000, opus_encoder=None
) -> None:
    """
    Convert raw audio bytes directly into Opus or PCM frames.
    """
    if file_type == "p3":
        # Decode `p3` directly.
        return p3.decode_opus_from_bytes_stream(audio_bytes, callback)
    else:
        # Decode all other formats through pydub.
        audio = AudioSegment.from_file(
            BytesIO(audio_bytes), format=file_type, parameters=["-nostdin"]
        )
        audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)
        raw_data = audio.raw_data
        pcm_to_data_stream(raw_data, is_opus, callback, sample_rate, opus_encoder)


def pcm_to_data_stream(raw_data, is_opus=True, callback: Callable[[Any], Any] = None, sample_rate=16000, opus_encoder=None):
    """
    Encode PCM data as a stream of Opus frames or output PCM directly.

    Args:
        raw_data: Raw PCM data.
        is_opus: Whether to encode as Opus.
        callback: Output callback.
        sample_rate: Sample rate.
        opus_encoder: Optional OpusEncoderUtils instance to preserve encoder state.
    """
    using_temp_encoder = False
    if is_opus and opus_encoder is None:
        encoder = opuslib_next.Encoder(sample_rate, 1, opuslib_next.APPLICATION_AUDIO)
        using_temp_encoder = True

    # Encoding parameters.
    frame_duration = 60  # 60ms per frame
    frame_size = int(sample_rate * frame_duration / 1000)  # samples/frame

    # Process every frame, padding the final one if required.
    for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
        # Read the current frame bytes.
        chunk = raw_data[i : i + frame_size * 2]

        # Pad the last frame with zeros if needed.
        if len(chunk) < frame_size * 2:
            chunk += b"\x00" * (frame_size * 2 - len(chunk))

        if is_opus:
            if using_temp_encoder:
                # Use a temporary encoder for standalone audio conversion.
                np_frame = np.frombuffer(chunk, dtype=np.int16)
                frame_data = encoder.encode(np_frame.tobytes(), frame_size)
                callback(frame_data)
            else:
                # Use the external encoder to preserve state across streamed TTS.
                is_last = (i + frame_size * 2 >= len(raw_data))
                opus_encoder.encode_pcm_to_opus_stream(chunk, end_of_stream=is_last, callback=callback)
        else:
            # In PCM mode, emit the chunk directly.
            frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)
            callback(frame_data)


def opus_datas_to_wav_bytes(opus_datas, sample_rate=16000, channels=1):
    """
    Decode a list of Opus frames into a WAV byte stream.
    """
    decoder = opuslib_next.Decoder(sample_rate, channels)
    try:
        pcm_datas = []

        frame_duration = 60  # ms
        frame_size = int(sample_rate * frame_duration / 1000)  # 960

        for opus_frame in opus_datas:
            # Decode into PCM bytes (2 bytes per sample).
            pcm = decoder.decode(opus_frame, frame_size)
            pcm_datas.append(pcm)

        pcm_bytes = b"".join(pcm_datas)

        # Write the WAV byte stream.
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return wav_buffer.getvalue()
    finally:
        if decoder is not None:
            try:
                del decoder
            except Exception:
                pass


def check_vad_update(before_config, new_config):
    if (
        new_config.get("selected_module") is None
        or new_config["selected_module"].get("VAD") is None
    ):
        return False
    update_vad = False
    current_vad_module = before_config["selected_module"]["VAD"]
    new_vad_module = new_config["selected_module"]["VAD"]
    current_vad_type = (
        current_vad_module
        if "type" not in before_config["VAD"][current_vad_module]
        else before_config["VAD"][current_vad_module]["type"]
    )
    new_vad_type = (
        new_vad_module
        if "type" not in new_config["VAD"][new_vad_module]
        else new_config["VAD"][new_vad_module]["type"]
    )
    update_vad = current_vad_type != new_vad_type
    return update_vad


def check_asr_update(before_config, new_config):
    if (
        new_config.get("selected_module") is None
        or new_config["selected_module"].get("ASR") is None
    ):
        return False
    update_asr = False
    current_asr_module = before_config["selected_module"]["ASR"]
    new_asr_module = new_config["selected_module"]["ASR"]

    # Any module name change requires an update.
    if current_asr_module != new_asr_module:
        return True

    # If the module name is unchanged, compare the effective type.
    current_asr_type = (
        current_asr_module
        if "type" not in before_config["ASR"][current_asr_module]
        else before_config["ASR"][current_asr_module]["type"]
    )
    new_asr_type = (
        new_asr_module
        if "type" not in new_config["ASR"][new_asr_module]
        else new_config["ASR"][new_asr_module]["type"]
    )
    update_asr = current_asr_type != new_asr_type
    return update_asr


def filter_sensitive_info(config: dict) -> dict:
    """
    Filter sensitive information out of a config dictionary.

    Args:
        config: Original config dictionary.

    Returns:
        Filtered config dictionary.
    """
    sensitive_keys = [
        "api_key",
        "personal_access_token",
        "access_token",
        "token",
        "secret",
        "access_key_secret",
        "secret_key",
    ]

    def _filter_dict(d: dict) -> dict:
        filtered = {}
        for k, v in d.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                filtered[k] = "***"
            elif isinstance(v, dict):
                filtered[k] = _filter_dict(v)
            elif isinstance(v, list):
                filtered[k] = [_filter_dict(i) if isinstance(i, dict) else i for i in v]
            elif isinstance(v, str):
                try:
                    json_data = json.loads(v)
                    if isinstance(json_data, dict):
                        filtered[k] = json.dumps(
                            _filter_dict(json_data), ensure_ascii=False
                        )
                    else:
                        filtered[k] = v
                except (json.JSONDecodeError, TypeError):
                    filtered[k] = v
            else:
                filtered[k] = v
        return filtered

    return _filter_dict(copy.deepcopy(config))


def get_vision_url(config: dict) -> str:
    """Get the vision URL.

    Args:
        config: Config dictionary.

    Returns:
        str: vision URL
    """
    server_config = config["server"]
    vision_explain = server_config.get("vision_explain", "")
    legacy_placeholder = "\u4f60\u7684"
    if legacy_placeholder in vision_explain or "your" in vision_explain.lower():
        local_ip = get_local_ip()
        port = int(server_config.get("http_port", 8003))
        vision_explain = f"http://{local_ip}:{port}/mcp/vision/explain"
    return vision_explain


def is_valid_image_file(file_data: bytes) -> bool:
    """
    Check whether file data matches a valid image format.

    Args:
        file_data: Binary file data.

    Returns:
        bool: `True` for a valid image format, otherwise `False`.
    """
    # Common image file signatures.
    image_signatures = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG\r\n\x1a\n": "PNG",
        b"GIF87a": "GIF",
        b"GIF89a": "GIF",
        b"BM": "BMP",
        b"II*\x00": "TIFF",
        b"MM\x00*": "TIFF",
        b"RIFF": "WEBP",
    }

    # Check whether the file header matches any known image signature.
    for signature in image_signatures:
        if file_data.startswith(signature):
            return True

    return False


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool names for OpenAI compatibility."""
    # Allow Chinese characters, ASCII letters, digits, underscores, and hyphens.
    return re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]", "_", name)


def validate_mcp_endpoint(mcp_endpoint: str) -> bool:
    """
    Validate the MCP endpoint format.

    Args:
        mcp_endpoint: MCP endpoint string.

    Returns:
        bool: Whether the endpoint is valid.
    """
    # 1. It must start with `ws`.
    if not mcp_endpoint.startswith("ws"):
        return False

    # 2. Reject placeholders containing key/call wording.
    if "key" in mcp_endpoint.lower() or "call" in mcp_endpoint.lower():
        return False

    # 3. It must include `/mcp/`.
    if "/mcp/" not in mcp_endpoint:
        return False

    return True

def get_system_error_response(config: dict) -> str:
    """Get the fallback reply used for system errors.

    Args:
        config: Config dictionary.

    Returns:
        str: System-error fallback reply.
    """
    return config.get(
        "system_error_response",
        "I'm a little busy right now. Let's try again in a moment.",
    )
