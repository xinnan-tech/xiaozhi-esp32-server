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

def get_ip_info(client_ip=None, logger=None):
    """
    Resolves location based on public IP. 
    If client_ip is local, it fetches the server's public IP.
    """
    import requests
    
    # Check if IP is private/local
    is_local = not client_ip or is_private_ip(client_ip)
    
    try:
        # Use ip-api.com (reliable and returns JSON)
        # If local, calling without an IP returns the public IP of your Durham gateway
        url = "http://ip-api.com/json/" if is_local else f"http://ip-api.com/json/{client_ip}"
        response = requests.get(url, timeout=5).json()
        
        if response.get("status") == "success":
            return {
                "city": response.get("city"),
                "lat": response.get("lat"),
                "lon": response.get("lon"),
                "region": response.get("regionName")
            }
    except Exception as e:
        if logger: logger.error(f"GeoIP Lookup failed: {e}")
    return None

def write_json_file(file_path, data):
    """Write data to JSON file"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def remove_punctuation_and_length(text):
    # Unicode range for full-width and half-width punctuation
    full_width_punctuations = (
        "！＂＃＄％＆＇（）＊＋，－。／：；＜＝＞？＠［＼］＾＿｀｛｜｝～"
    )
    half_width_punctuations = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    space = " "  # Half-width space
    full_width_space = "  "  # Full-width space

    # Remove full-width and half-width punctuation and spaces
    result = "".join(
        [
            char
            for char in text
            if char not in full_width_punctuations
            and char not in half_width_punctuations
        ]
    )

    # Aggressive filtering for "Yeah", "I", "I." and variants
    cleaned = result.strip().lower()
    if cleaned in ["yeah", "yeah.", "i", "i."]:
        return 0, ""

    return len(result), result


def check_for_noise(pcm_data: bytes) -> bool:
    """
    Check if audio data is likely noise/silence based on energy.
    Criteria:
    1. Total Energy ave(sum of squares) < 600
    2. Max value < 1000
    """
    if not pcm_data:
        return True
    
    ms_threshold = 600.0
    # Convert to 16-bit integers
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    
    # Energy = mean(sample^2)
    # Using astype(np.float64) to ensure precision and avoid overflow
    energy = np.mean(samples.astype(np.float64) ** 2)
    if energy < ms_threshold:
        return True
    
    max_threshold = 1000
    # Check absolute max value (amplitude)
    maxvalue = np.max(np.abs(samples))
    if maxvalue < max_threshold:
        return True

    return False


def check_model_key(modelType, modelKey):
    if "你" in modelKey:
        return f"Config error: API key for {modelType} not set, current value: {modelKey}"
    return None


def parse_string_to_list(value, separator=";"):
    """
    Convert input value to list
    Args:
        value: Input value, can be None, string or list
        separator: Separator, default is semicolon
    Returns:
        list: Processed list
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
    Check if ffmpeg is correctly installed and executable in the current environment.

    Returns:
        bool: Returns True if ffmpeg is available; otherwise raises ValueError.

    Raises:
        ValueError: Raises detailed error message when ffmpeg is not installed or dependencies are missing.
    """
    try:
        # Try to execute ffmpeg command
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # Non-zero exit code triggers CalledProcessError
        )

        output = (result.stdout + result.stderr).lower()
        if "ffmpeg version" in output:
            return True

        # If version info not detected, consider as exception
        raise ValueError("No valid ffmpeg version output detected.")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Extract error output
        stderr_output = ""
        if isinstance(e, subprocess.CalledProcessError):
            stderr_output = (e.stderr or "").strip()
        else:
            stderr_output = str(e).strip()

        # Build basic error message
        error_msg = [
            "❌ FFmpeg cannot run normally.\n",
            "Suggestion:",
            "1. Ensure conda environment is activated correctly;",
            "2. Refer to project installation docs to install ffmpeg in conda environment.\n",
        ]

        # 🎯 Provide extra tips for specific error messages
        if "libiconv.so.2" in stderr_output:
            error_msg.append("⚠️ Missing dependency: libiconv.so.2")
            error_msg.append("Solution: Run in current conda environment:")
            error_msg.append("   conda install -c conda-forge libiconv\n")
        elif (
            "no such file or directory" in stderr_output
            and "ffmpeg" in stderr_output.lower()
        ):
            error_msg.append("⚠️ FFmpeg executable not found.")
            error_msg.append("Solution: Run in current conda environment:")
            error_msg.append("   conda install -c conda-forge ffmpeg\n")
        else:
            error_msg.append("Error details:")
            error_msg.append(stderr_output or "Unknown error.")

        # Raise detailed exception info
        raise ValueError("\n".join(error_msg)) from e


def extract_json_from_string(input_string):
    """Extract JSON part from string"""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string, re.DOTALL)  # Add re.DOTALL
    if match:
        return match.group(1)  # Return extracted JSON string
    return None


def audio_to_data_stream(
    audio_file_path, is_opus=True, callback: Callable[[Any], Any] = None
) -> None:
    # Get file extension
    file_type = os.path.splitext(audio_file_path)[1]
    if file_type:
        file_type = file_type.lstrip(".")
    # Read audio file, -nostdin parameter: do not read data from stdin, otherwise FFmpeg will block
    audio = AudioSegment.from_file(
        audio_file_path, format=file_type, parameters=["-nostdin"]
    )

    # Convert to mono/16kHz sample rate/16-bit little endian (ensure match with encoder)
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    # Append 200ms silence to prevent voxing
    audio += AudioSegment.silent(duration=200)

    # Get raw PCM data (16-bit little endian)
    raw_data = audio.raw_data
    pcm_to_data_stream(raw_data, is_opus, callback)


async def audio_to_data(
    audio_file_path: str, is_opus: bool = True, use_cache: bool = True
) -> list[bytes]:
    """
    Convert audio file to Opus/PCM encoded frame list
    Args:
        audio_file_path: Audio file path
        is_opus: Whether to perform Opus encoding
        use_cache: Whether to use cache
    """
    from core.utils.cache.manager import cache_manager
    from core.utils.cache.config import CacheType

    # Generate cache key, including file path and encoding type
    cache_key = f"{audio_file_path}:{is_opus}"

    # Try to get result from cache
    if use_cache:
        cached_result = cache_manager.get(CacheType.AUDIO_DATA, cache_key)
        if cached_result is not None:
            return cached_result

    def _sync_audio_to_data():
        # Get file extension
        file_type = os.path.splitext(audio_file_path)[1]
        if file_type:
            file_type = file_type.lstrip(".")
        # Read audio file, -nostdin parameter: do not read data from stdin, otherwise FFmpeg will block
        audio = AudioSegment.from_file(
            audio_file_path, format=file_type, parameters=["-nostdin"]
        )

        # Convert to mono/16kHz sample rate/16-bit little endian (ensure match with encoder)
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        # Append 200ms silence to prevent voxing
        audio += AudioSegment.silent(duration=200)

        # Get raw PCM data (16-bit little endian)
        raw_data = audio.raw_data

        # Initialize Opus encoder
        encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)

        # Encoding parameters
        frame_duration = 60  # 60ms per frame
        frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

        datas = []
        # Process all audio data frame by frame (including padding zero for last frame)
        for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
            # Get binary data of current frame
            chunk = raw_data[i : i + frame_size * 2]

            # If last frame is insufficient, pad with zeros
            if len(chunk) < frame_size * 2:
                chunk += b"\x00" * (frame_size * 2 - len(chunk))

            if is_opus:
                # Convert to numpy array for processing
                np_frame = np.frombuffer(chunk, dtype=np.int16)
                # Encode Opus data
                frame_data = encoder.encode(np_frame.tobytes(), frame_size)
            else:
                frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)

            datas.append(frame_data)

        return datas

    loop = asyncio.get_running_loop()
    # Execute synchronous audio processing operations in a separate thread
    result = await loop.run_in_executor(None, _sync_audio_to_data)

    # Save result to cache using TTL defined in config (10 minutes)
    if use_cache:
        cache_manager.set(CacheType.AUDIO_DATA, cache_key, result)

    return result


def audio_bytes_to_data_stream(
    audio_bytes, file_type, is_opus, callback: Callable[[Any], Any]
) -> None:
    """
    Directly convert audio binary data to opus/pcm data, supports wav, mp3, p3
    """
    if file_type == "p3":
        # Decode using p3 directly
        return p3.decode_opus_from_bytes_stream(audio_bytes, callback)
    else:
        # Use pydub for other formats
        audio = AudioSegment.from_file(
            BytesIO(audio_bytes), format=file_type, parameters=["-nostdin"]
        )
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        # Append 200ms silence to prevent voxing
        audio += AudioSegment.silent(duration=200)
        raw_data = audio.raw_data
        pcm_to_data_stream(raw_data, is_opus, callback)


def pcm_to_data_stream(raw_data, is_opus=True, callback: Callable[[Any], Any] = None):
    # Initialize Opus encoder
    encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)

    # Encoding parameters
    frame_duration = 60  # 60ms per frame
    frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

    # Process all audio data frame by frame (including padding zero for last frame)
    for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
        # Get binary data of current frame
        chunk = raw_data[i : i + frame_size * 2]

        # If last frame is insufficient, pad with zeros
        if len(chunk) < frame_size * 2:
            chunk += b"\x00" * (frame_size * 2 - len(chunk))

        if is_opus:
            # Convert to numpy array for processing
            np_frame = np.frombuffer(chunk, dtype=np.int16)
            # Encode Opus data
            frame_data = encoder.encode(np_frame.tobytes(), frame_size)
            callback(frame_data)
        else:
            frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)
            callback(frame_data)


def opus_datas_to_wav_bytes(opus_datas, sample_rate=16000, channels=1):
    """
    Decode opus frame list to wav byte stream
    """
    decoder = opuslib_next.Decoder(sample_rate, channels)
    try:
        pcm_datas = []

        frame_duration = 60  # ms
        frame_size = int(sample_rate * frame_duration / 1000)  # 960

        for opus_frame in opus_datas:
            # Decode to PCM (return bytes, 2 bytes/sample)
            pcm = decoder.decode(opus_frame, frame_size)
            pcm_datas.append(pcm)

        pcm_bytes = b"".join(pcm_datas)

        # Write wav byte stream
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
    Filter sensitive info in config
    Args:
        config: Original config dict
    Returns:
        Filtered config dict
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
    """Get vision URL

    Args:
        config: Config dict

    Returns:
        str: vision URL
    """
    server_config = config["server"]
    vision_explain = server_config.get("vision_explain", "")
    if "你的" in vision_explain:
        local_ip = get_local_ip()
        port = int(server_config.get("http_port", 8003))
        vision_explain = f"http://{local_ip}:{port}/mcp/vision/explain"
    return vision_explain


def is_valid_image_file(file_data: bytes) -> bool:
    """
    Check if file data is valid image format

    Args:
        file_data: Binary data of file

    Returns:
        bool: Return True if valid image format, else False
    """
    # Magic numbers for common image formats (file headers)
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

    # Check if file header matches any known image formats
    for signature in image_signatures:
        if file_data.startswith(signature):
            return True

    return False


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool names for OpenAI compatibility."""
    # Supports Chinese, English letters, numbers, underscores and hyphens
    return re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]", "_", name)


def validate_mcp_endpoint(mcp_endpoint: str) -> bool:
    """
    Validate MCP endpoint format

    Args:
        mcp_endpoint: MCP endpoint string

    Returns:
        bool: Whether valid
    """
    # 1. Check if starts with ws
    if not mcp_endpoint.startswith("ws"):
        return False

    # 2. Check if contains key, call words
    if "key" in mcp_endpoint.lower() or "call" in mcp_endpoint.lower():
        return False

    # 3. Check if contains /mcp/ string
    if "/mcp/" not in mcp_endpoint:
        return False

    return True

def fetch_lat_lon(location):
    """
    Resolve city name to Lat/Lon using Open-Meteo Geocoding API (Free).
    """
    import requests
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
    
    try:
        # We don't have access to logger here easily without circular import if we init it, 
        # so we'll just print or use logging.getLogger if needed, or rely on caller to log failure if returns None.
        # But actually we can import setup_logging inside function or at top if not circular.
        # core/utils/util.py doesn't seem to import config.logger at top (wait, it does line 17? No.)
        # Let's check imports. line 496 `from config.logger import setup_logging`? No.
        # We will skip logging inside this util function for simplicity or use print/standard logging if critical.
        # Actually simplest is just to request content.
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return result["latitude"], result["longitude"], f"{result['name']}, {result.get('admin1', '')}"
        
        return None, None, None
    except Exception:
        return None, None, None
