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
        # 导入全局缓存管理器
        from core.utils.cache.manager import cache_manager, CacheType

        # 先从缓存获取
        cached_ip_info = cache_manager.get(CacheType.IP_INFO, ip_addr)
        if cached_ip_info is not None:
            return cached_ip_info

        # 缓存未命中，调用API
        if is_private_ip(ip_addr):
            ip_addr = ""
        url = f"https://whois.pconline.com.cn/ipJson.jsp?json=true&ip={ip_addr}"
        resp = requests.get(url).json()
        ip_info = {"city": resp.get("city")}

        # 存入缓存
        cache_manager.set(CacheType.IP_INFO, ip_addr, ip_info)
        return ip_info
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting client ip info: {e}")
        return {}


def write_json_file(file_path, data):
    """将数据写入 JSON 文件"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def remove_punctuation_and_length(text):
    # 全角符号和半角符号的Unicode范围
    full_width_punctuations = (
        "！＂＃＄％＆＇（）＊＋，－。／：；＜＝＞？＠［＼］＾＿｀｛｜｝～"
    )
    half_width_punctuations = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    space = " "  # 半角空格
    full_width_space = "　"  # 全角空格

    # 去除全角和半角符号以及空格
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
    if "你" in modelKey:
        return f"配置错误: {modelType} 的 API key 未设置,当前值为: {modelKey}"
    return None


def parse_string_to_list(value, separator=";"):
    """
    将输入值转换为列表
    Args:
        value: 输入值，可以是 None、字符串或列表
        separator: 分隔符，默认为分号
    Returns:
        list: 处理后的列表
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
    检查当前环境中是否已正确安装并可执行 ffmpeg。

    Returns:
        bool: 如果 ffmpeg 正常可用，返回 True；否则抛出 ValueError 异常。

    Raises:
        ValueError: 当检测到 ffmpeg 未安装或依赖缺失时，抛出详细的提示信息。
    """
    try:
        # 尝试执行 ffmpeg 命令
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # 非零退出码会触发 CalledProcessError
        )

        output = (result.stdout + result.stderr).lower()
        if "ffmpeg version" in output:
            return True

        # 如果未检测到版本信息，也视为异常情况
        raise ValueError("未检测到有效的 ffmpeg 版本输出。")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # 提取错误输出
        stderr_output = ""
        if isinstance(e, subprocess.CalledProcessError):
            stderr_output = (e.stderr or "").strip()
        else:
            stderr_output = str(e).strip()

        # 构建基础错误提示
        error_msg = [
            "❌ 检测到 ffmpeg 无法正常运行。\n",
            "建议您：",
            "1. 确认已正确激活 conda 环境；",
            "2. 查阅项目安装文档，了解如何在 conda 环境中安装 ffmpeg。\n",
        ]

        # 🎯 针对具体错误信息提供额外提示
        if "libiconv.so.2" in stderr_output:
            error_msg.append("⚠️ 发现缺少依赖库：libiconv.so.2")
            error_msg.append("解决方法：在当前 conda 环境中执行：")
            error_msg.append("   conda install -c conda-forge libiconv\n")
        elif (
            "no such file or directory" in stderr_output
            and "ffmpeg" in stderr_output.lower()
        ):
            error_msg.append("⚠️ 系统未找到 ffmpeg 可执行文件。")
            error_msg.append("解决方法：在当前 conda 环境中执行：")
            error_msg.append("   conda install -c conda-forge ffmpeg\n")
        else:
            error_msg.append("错误详情：")
            error_msg.append(stderr_output or "未知错误。")

        # 抛出详细异常信息
        raise ValueError("\n".join(error_msg)) from e


def extract_json_from_string(input_string):
    """提取字符串中的 JSON 部分"""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string, re.DOTALL)  # 添加 re.DOTALL
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None


def audio_to_data_stream(
    audio_file_path, is_opus=True, callback: Callable[[Any], Any] = None, sample_rate=16000, opus_encoder=None
) -> None:
    # 获取文件后缀名
    file_type = os.path.splitext(audio_file_path)[1]
    if file_type:
        file_type = file_type.lstrip(".")
    # 读取音频文件，-nostdin 参数：不要从标准输入读取数据，否则FFmpeg会阻塞
    audio = AudioSegment.from_file(
        audio_file_path, format=file_type, parameters=["-nostdin"]
    )

    # 转换为单声道/指定采样率/16位小端编码（确保与编码器匹配）
    audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)

    # 获取原始PCM数据（16位小端）
    raw_data = audio.raw_data
    pcm_to_data_stream(raw_data, is_opus, callback, sample_rate, opus_encoder)


async def audio_to_data(
    audio_file_path: str, is_opus: bool = True, use_cache: bool = True
) -> list[bytes]:
    """
    将音频文件转换为Opus/PCM编码的帧列表
    Args:
        audio_file_path: 音频文件路径
        is_opus: 是否进行Opus编码
        use_cache: 是否使用缓存
    """
    from core.utils.cache.manager import cache_manager
    from core.utils.cache.config import CacheType

    # 生成缓存键，包含文件路径和编码类型
    cache_key = f"{audio_file_path}:{is_opus}"

    # 尝试从缓存获取结果
    if use_cache:
        cached_result = cache_manager.get(CacheType.AUDIO_DATA, cache_key)
        if cached_result is not None:
            return cached_result

    def _sync_audio_to_data():
        # 获取文件后缀名
        file_type = os.path.splitext(audio_file_path)[1]
        if file_type:
            file_type = file_type.lstrip(".")
        # 读取音频文件，-nostdin 参数：不要从标准输入读取数据，否则FFmpeg会阻塞
        audio = AudioSegment.from_file(
            audio_file_path, format=file_type, parameters=["-nostdin"]
        )

        # 转换为单声道/16kHz采样率/16位小端编码（确保与编码器匹配）
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

        # 获取原始PCM数据（16位小端）
        raw_data = audio.raw_data

        # 初始化Opus编码器
        encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)

        # 编码参数
        frame_duration = 60  # 60ms per frame
        frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

        datas = []
        # 按帧处理所有音频数据（包括最后一帧可能补零）
        for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
            # 获取当前帧的二进制数据
            chunk = raw_data[i : i + frame_size * 2]

            # 如果最后一帧不足，补零
            if len(chunk) < frame_size * 2:
                chunk += b"\x00" * (frame_size * 2 - len(chunk))

            if is_opus:
                # 转换为numpy数组处理
                np_frame = np.frombuffer(chunk, dtype=np.int16)
                # 编码Opus数据
                frame_data = encoder.encode(np_frame.tobytes(), frame_size)
            else:
                frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)

            datas.append(frame_data)

        return datas

    loop = asyncio.get_running_loop()
    # 在单独的线程中执行同步的音频处理操作
    result = await loop.run_in_executor(None, _sync_audio_to_data)

    # 将结果存入缓存，使用配置中定义的TTL（10分钟）
    if use_cache:
        cache_manager.set(CacheType.AUDIO_DATA, cache_key, result)

    return result


def audio_bytes_to_data_stream(
    audio_bytes, file_type, is_opus, callback: Callable[[Any], Any], sample_rate=16000, opus_encoder=None
) -> None:
    """
    直接用音频二进制数据转为opus/pcm数据，支持wav、mp3、p3
    """
    if file_type == "p3":
        # 直接用p3解码
        return p3.decode_opus_from_bytes_stream(audio_bytes, callback)
    else:
        # 其他格式用pydub
        audio = AudioSegment.from_file(
            BytesIO(audio_bytes), format=file_type, parameters=["-nostdin"]
        )
        audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)
        raw_data = audio.raw_data
        pcm_to_data_stream(raw_data, is_opus, callback, sample_rate, opus_encoder)


def pcm_to_data_stream(raw_data, is_opus=True, callback: Callable[[Any], Any] = None, sample_rate=16000, opus_encoder=None):
    """
    将PCM数据流式编码为Opus或直接输出PCM

    Args:
        raw_data: PCM原始数据
        is_opus: 是否编码为Opus
        callback: 回调函数
        sample_rate: 采样率
        opus_encoder: OpusEncoderUtils对象(推荐提供以保持编码器状态连续)
    """
    using_temp_encoder = False
    if is_opus and opus_encoder is None:
        encoder = opuslib_next.Encoder(sample_rate, 1, opuslib_next.APPLICATION_AUDIO)
        using_temp_encoder = True

    # 编码参数
    frame_duration = 60  # 60ms per frame
    frame_size = int(sample_rate * frame_duration / 1000)  # samples/frame

    # 按帧处理所有音频数据（包括最后一帧可能补零）
    for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
        # 获取当前帧的二进制数据
        chunk = raw_data[i : i + frame_size * 2]

        # 如果最后一帧不足，补零
        if len(chunk) < frame_size * 2:
            chunk += b"\x00" * (frame_size * 2 - len(chunk))

        if is_opus:
            if using_temp_encoder:
                # 使用临时编码器（仅用于独立音频场景）
                np_frame = np.frombuffer(chunk, dtype=np.int16)
                frame_data = encoder.encode(np_frame.tobytes(), frame_size)
                callback(frame_data)
            else:
                # 使用外部编码器（TTS流式场景,保持状态连续）
                is_last = (i + frame_size * 2 >= len(raw_data))
                opus_encoder.encode_pcm_to_opus_stream(chunk, end_of_stream=is_last, callback=callback)
        else:
            # PCM模式,直接输出
            frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)
            callback(frame_data)


def opus_datas_to_wav_bytes(opus_datas, sample_rate=16000, channels=1):
    """
    将opus帧列表解码为wav字节流
    """
    decoder = opuslib_next.Decoder(sample_rate, channels)
    try:
        pcm_datas = []

        frame_duration = 60  # ms
        frame_size = int(sample_rate * frame_duration / 1000)  # 960

        for opus_frame in opus_datas:
            # 解码为PCM（返回bytes，2字节/采样点）
            pcm = decoder.decode(opus_frame, frame_size)
            pcm_datas.append(pcm)

        pcm_bytes = b"".join(pcm_datas)

        # 写入wav字节流
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

    # 如果模块名称不同，就需要更新
    if current_asr_module != new_asr_module:
        return True

    # 如果模块名称相同，再比较类型
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
    过滤配置中的敏感信息
    Args:
        config: 原始配置字典
    Returns:
        过滤后的配置字典
    """
    sensitive_keys = [
        "api_key",
        "personal_access_token",
        "access_token",
        "token",
        "secret",
        "access_key_secret",
        "secret_key",
        "private_key",
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
    """获取 vision URL

    Args:
        config: 配置字典

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
    检查文件数据是否为有效的图片格式

    Args:
        file_data: 文件的二进制数据

    Returns:
        bool: 如果是有效的图片格式返回True，否则返回False
    """
    # 常见图片格式的魔数（文件头）
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

    # 检查文件头是否匹配任何已知的图片格式
    for signature in image_signatures:
        if file_data.startswith(signature):
            return True

    return False


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool names for OpenAI compatibility."""
    # 支持中文、英文字母、数字、下划线和连字符
    return re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]", "_", name)


def validate_mcp_endpoint(mcp_endpoint: str) -> bool:
    """
    校验MCP接入点格式

    Args:
        mcp_endpoint: MCP接入点字符串

    Returns:
        bool: 是否有效
    """
    # 1. 检查是否以ws开头
    if not mcp_endpoint.startswith("ws"):
        return False

    # 2. 检查是否包含key、call字样
    if "key" in mcp_endpoint.lower() or "call" in mcp_endpoint.lower():
        return False

    # 3. 检查是否包含/mcp/字样
    if "/mcp/" not in mcp_endpoint:
        return False

    return True

def get_system_error_response(config: dict) -> str:
    """获取系统错误时的回复

    Args:
        config: 配置字典

    Returns:
        str: 系统错误时的回复
    """
    return config.get("system_error_response", "主人，小智现在有点忙，我们稍后再试吧。")
