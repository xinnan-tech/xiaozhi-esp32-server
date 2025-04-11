import os
import json
import socket
import subprocess
import logging
import re
import requests
from typing import Dict, Any
from core.utils import tts, llm, intent, memory, vad, asr


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


def get_ip_info(ip_addr):
    try:
        if is_private_ip(ip_addr):
            ip_addr = ""
        url = f"https://whois.pconline.com.cn/ipJson.jsp?json=true&ip={ip_addr}"
        resp = requests.get(url).json()
        ip_info = {"city": resp.get("city")}
        return ip_info
    except Exception as e:
        logging.error(f"Error getting client ip info: {e}")
        return {}


def write_json_file(file_path, data):
    """将数据写入 JSON 文件"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def is_punctuation_or_emoji(char):
    """检查字符是否为空格、指定标点或表情符号"""
    # 定义需要去除的中英文标点（包括全角/半角）
    punctuation_set = {
        "，",
        ",",  # 中文逗号 + 英文逗号
        "。",
        ".",  # 中文句号 + 英文句号
        "！",
        "!",  # 中文感叹号 + 英文感叹号
        "-",
        "－",  # 英文连字符 + 中文全角横线
        "、",  # 中文顿号
    }
    if char.isspace() or char in punctuation_set:
        return True
    # 检查表情符号（保留原有逻辑）
    code_point = ord(char)
    emoji_ranges = [
        (0x1F600, 0x1F64F),
        (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]
    return any(start <= code_point <= end for start, end in emoji_ranges)


def get_string_no_punctuation_or_emoji(s):
    """去除字符串首尾的空格、标点符号和表情符号"""
    chars = list(s)
    # 处理开头的字符
    start = 0
    while start < len(chars) and is_punctuation_or_emoji(chars[start]):
        start += 1
    # 处理结尾的字符
    end = len(chars) - 1
    while end >= start and is_punctuation_or_emoji(chars[end]):
        end -= 1
    return "".join(chars[start : end + 1])


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
        logging.error(
            "你还没配置"
            + modelType
            + "的密钥，请在配置文件中配置密钥，否则无法正常工作"
        )
        return False
    return True


def check_ffmpeg_installed():
    ffmpeg_installed = False
    try:
        # 执行ffmpeg -version命令，并捕获输出
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # 如果返回码非零则抛出异常
        )
        # 检查输出中是否包含版本信息（可选）
        output = result.stdout + result.stderr
        if "ffmpeg version" in output.lower():
            ffmpeg_installed = True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 命令执行失败或未找到
        ffmpeg_installed = False
    if not ffmpeg_installed:
        error_msg = "您的电脑还没正确安装ffmpeg\n"
        error_msg += "\n建议您：\n"
        error_msg += "1、按照项目的安装文档，正确进入conda环境\n"
        error_msg += "2、查阅安装文档，如何在conda环境中安装ffmpeg\n"
        raise ValueError(error_msg)


def extract_json_from_string(input_string):
    """提取字符串中的 JSON 部分"""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None


def initialize_modules(
    config: Dict[str, Any],
    init_vad=True,
    init_asr=True,
    init_llm=True,
    init_tts=True,
    init_memory=True,
    init_intent=True,
) -> Dict[str, Any]:
    """
    初始化所有模块组件

    Args:
        config: 配置字典

    Returns:
        Dict[str, Any]: 包含所有初始化后的模块的字典
    """
    modules = {}

    # 初始化TTS模块
    if init_tts:
        tts_type = (
            config["selected_module"]["TTS"]
            if "type" not in config["TTS"][config["selected_module"]["TTS"]]
            else config["TTS"][config["selected_module"]["TTS"]]["type"]
        )
        modules["tts"] = tts.create_instance(
            tts_type,
            config["TTS"][config["selected_module"]["TTS"]],
            config["delete_audio"],
        )

    # 初始化LLM模块
    if init_llm:
        llm_type = (
            config["selected_module"]["LLM"]
            if "type" not in config["LLM"][config["selected_module"]["LLM"]]
            else config["LLM"][config["selected_module"]["LLM"]]["type"]
        )
        modules["llm"] = llm.create_instance(
            llm_type,
            config["LLM"][config["selected_module"]["LLM"]],
        )

    # 初始化Intent模块
    if init_intent:
        intent_type = (
            config["selected_module"]["Intent"]
            if "type" not in config["Intent"][config["selected_module"]["Intent"]]
            else config["Intent"][config["selected_module"]["Intent"]]["type"]
        )
        modules["intent"] = intent.create_instance(
            intent_type,
            config["Intent"][config["selected_module"]["Intent"]],
        )

    # 初始化Memory模块
    if init_memory:
        memory_type = (
            config["selected_module"]["Memory"]
            if "type" not in config["Memory"][config["selected_module"]["Memory"]]
            else config["Memory"][config["selected_module"]["Memory"]]["type"]
        )
        modules["memory"] = memory.create_instance(
            memory_type,
            config["Memory"][config["selected_module"]["Memory"]],
        )

    # 初始化VAD模块
    if init_vad:
        vad_type = (
            config["selected_module"]["VAD"]
            if "type" not in config["VAD"][config["selected_module"]["VAD"]]
            else config["VAD"][config["selected_module"]["VAD"]]["type"]
        )
        modules["vad"] = vad.create_instance(
            vad_type,
            config["VAD"][config["selected_module"]["VAD"]],
        )

    # 初始化ASR模块
    if init_asr:
        asr_type = (
            config["selected_module"]["ASR"]
            if "type" not in config["ASR"][config["selected_module"]["ASR"]]
            else config["ASR"][config["selected_module"]["ASR"]]["type"]
        )
        modules["asr"] = asr.create_instance(
            asr_type,
            config["ASR"][config["selected_module"]["ASR"]],
            config["delete_audio"],
        )

    return modules
