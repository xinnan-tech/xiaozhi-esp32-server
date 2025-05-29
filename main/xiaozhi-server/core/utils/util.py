import json
import socket
import subprocess
import re
import os
import numpy as np
import requests
import opuslib_next
from pydub import AudioSegment
from typing import Dict, Any
from core.utils import tts, llm, intent, memory, vad, asr
import copy

TAG = __name__
emoji_map = {
    "neutral": "😶",
    "happy": "🙂",
    "laughing": "😆",
    "funny": "😂",
    "sad": "😔",
    "angry": "😠",
    "crying": "😭",
    "loving": "😍",
    "embarrassed": "😳",
    "surprised": "😲",
    "shocked": "😱",
    "thinking": "🤔",
    "winking": "😉",
    "cool": "😎",
    "relaxed": "😌",
    "delicious": "🤤",
    "kissy": "😘",
    "confident": "😏",
    "sleepy": "😴",
    "silly": "😜",
    "confused": "🙄",
}


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
        if is_private_ip(ip_addr):
            ip_addr = ""
        url = f"https://whois.pconline.com.cn/ipJson.jsp?json=true&ip={ip_addr}"
        resp = requests.get(url).json()
        ip_info = {"city": resp.get("city")}
        return ip_info
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting client ip info: {e}")
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
        "-",
        "－",  # 英文连字符 + 中文全角横线
        "、",  # 中文顿号
        "“",
        "”",
        '"',  # 中文双引号 + 英文引号
        "：",
        ":",  # 中文冒号 + 英文冒号
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
        raise ValueError(
            "你还没配置" + modelType + "的密钥，请检查一下所使用的LLM是否配置了密钥"
        )
    return True


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
    match = re.search(pattern, input_string, re.DOTALL)  # 添加 re.DOTALL
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None


def initialize_modules(
    logger,
    config: Dict[str, Any],
    init_vad=False,
    init_asr=False,
    init_llm=False,
    init_tts=False,
    init_memory=False,
    init_intent=False,
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
        select_tts_module = config["selected_module"]["TTS"]
        modules["tts"] = initialize_tts(config)
        logger.bind(tag=TAG).info(f"初始化组件: tts成功 {select_tts_module}")

    # 初始化LLM模块
    if init_llm:
        select_llm_module = config["selected_module"]["LLM"]
        llm_type = (
            select_llm_module
            if "type" not in config["LLM"][select_llm_module]
            else config["LLM"][select_llm_module]["type"]
        )
        modules["llm"] = llm.create_instance(
            llm_type,
            config["LLM"][select_llm_module],
        )
        logger.bind(tag=TAG).info(f"初始化组件: llm成功 {select_llm_module}")

    # 初始化Intent模块
    if init_intent:
        select_intent_module = config["selected_module"]["Intent"]
        intent_type = (
            select_intent_module
            if "type" not in config["Intent"][select_intent_module]
            else config["Intent"][select_intent_module]["type"]
        )
        modules["intent"] = intent.create_instance(
            intent_type,
            config["Intent"][select_intent_module],
        )
        logger.bind(tag=TAG).info(f"初始化组件: intent成功 {select_intent_module}")

    # 初始化Memory模块
    if init_memory:
        select_memory_module = config["selected_module"]["Memory"]
        memory_type = (
            select_memory_module
            if "type" not in config["Memory"][select_memory_module]
            else config["Memory"][select_memory_module]["type"]
        )
        modules["memory"] = memory.create_instance(
            memory_type,
            config["Memory"][select_memory_module],
            config.get("summaryMemory", None),
        )
        logger.bind(tag=TAG).info(f"初始化组件: memory成功 {select_memory_module}")

    # 初始化VAD模块
    if init_vad:
        select_vad_module = config["selected_module"]["VAD"]
        vad_type = (
            select_vad_module
            if "type" not in config["VAD"][select_vad_module]
            else config["VAD"][select_vad_module]["type"]
        )
        modules["vad"] = vad.create_instance(
            vad_type,
            config["VAD"][select_vad_module],
        )
        logger.bind(tag=TAG).info(f"初始化组件: vad成功 {select_vad_module}")

    # 初始化ASR模块
    if init_asr:
        select_asr_module = config["selected_module"]["ASR"]
        asr_type = (
            select_asr_module
            if "type" not in config["ASR"][select_asr_module]
            else config["ASR"][select_asr_module]["type"]
        )
        modules["asr"] = asr.create_instance(
            asr_type,
            config["ASR"][select_asr_module],
            str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
        )
        logger.bind(tag=TAG).info(f"初始化组件: asr成功 {select_asr_module}")
    return modules


def initialize_tts(config):
    select_tts_module = config["selected_module"]["TTS"]
    tts_type = (
        select_tts_module
        if "type" not in config["TTS"][select_tts_module]
        else config["TTS"][select_tts_module]["type"]
    )
    new_tts = tts.create_instance(
        tts_type,
        config["TTS"][select_tts_module],
        str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
    )
    return new_tts


def analyze_emotion(text):
    """
    分析文本情感并返回对应的emoji名称（支持中英文）
    """
    if not text or not isinstance(text, str):
        return "neutral"

    original_text = text
    text = text.lower().strip()

    # 检查是否包含现有emoji
    for emotion, emoji in emoji_map.items():
        if emoji in original_text:
            return emotion

    # 标点符号分析
    has_exclamation = "!" in original_text or "！" in original_text
    has_question = "?" in original_text or "？" in original_text
    has_ellipsis = "..." in original_text or "…" in original_text

    # 定义情感关键词映射（中英文扩展版）
    emotion_keywords = {
        "happy": [
            "开心",
            "高兴",
            "快乐",
            "愉快",
            "幸福",
            "满意",
            "棒",
            "好",
            "不错",
            "完美",
            "棒极了",
            "太好了",
            "好呀",
            "好的",
            "happy",
            "joy",
            "great",
            "good",
            "nice",
            "awesome",
            "fantastic",
            "wonderful",
        ],
        "laughing": [
            "哈哈",
            "哈哈哈",
            "呵呵",
            "嘿嘿",
            "嘻嘻",
            "笑死",
            "太好笑了",
            "笑死我了",
            "lol",
            "lmao",
            "haha",
            "hahaha",
            "hehe",
            "rofl",
            "funny",
            "laugh",
        ],
        "funny": [
            "搞笑",
            "滑稽",
            "逗",
            "幽默",
            "笑点",
            "段子",
            "笑话",
            "太逗了",
            "hilarious",
            "joke",
            "comedy",
        ],
        "sad": [
            "伤心",
            "难过",
            "悲哀",
            "悲伤",
            "忧郁",
            "郁闷",
            "沮丧",
            "失望",
            "想哭",
            "难受",
            "不开心",
            "唉",
            "呜呜",
            "sad",
            "upset",
            "unhappy",
            "depressed",
            "sorrow",
            "gloomy",
        ],
        "angry": [
            "生气",
            "愤怒",
            "气死",
            "讨厌",
            "烦人",
            "可恶",
            "烦死了",
            "恼火",
            "暴躁",
            "火大",
            "愤怒",
            "气炸了",
            "angry",
            "mad",
            "annoyed",
            "furious",
            "pissed",
            "hate",
        ],
        "crying": [
            "哭泣",
            "泪流",
            "大哭",
            "伤心欲绝",
            "泪目",
            "流泪",
            "哭死",
            "哭晕",
            "想哭",
            "泪崩",
            "cry",
            "crying",
            "tears",
            "sob",
            "weep",
        ],
        "loving": [
            "爱你",
            "喜欢",
            "爱",
            "亲爱的",
            "宝贝",
            "么么哒",
            "抱抱",
            "想你",
            "思念",
            "最爱",
            "亲亲",
            "喜欢你",
            "love",
            "like",
            "adore",
            "darling",
            "sweetie",
            "honey",
            "miss you",
            "heart",
        ],
        "embarrassed": [
            "尴尬",
            "不好意思",
            "害羞",
            "脸红",
            "难为情",
            "社死",
            "丢脸",
            "出丑",
            "embarrassed",
            "awkward",
            "shy",
            "blush",
        ],
        "surprised": [
            "惊讶",
            "吃惊",
            "天啊",
            "哇塞",
            "哇",
            "居然",
            "竟然",
            "没想到",
            "出乎意料",
            "surprise",
            "wow",
            "omg",
            "oh my god",
            "amazing",
            "unbelievable",
        ],
        "shocked": [
            "震惊",
            "吓到",
            "惊呆了",
            "不敢相信",
            "震撼",
            "吓死",
            "恐怖",
            "害怕",
            "吓人",
            "shocked",
            "shocking",
            "scared",
            "frightened",
            "terrified",
            "horror",
        ],
        "thinking": [
            "思考",
            "考虑",
            "想一下",
            "琢磨",
            "沉思",
            "冥想",
            "想",
            "思考中",
            "在想",
            "think",
            "thinking",
            "consider",
            "ponder",
            "meditate",
        ],
        "winking": [
            "调皮",
            "眨眼",
            "你懂的",
            "坏笑",
            "邪恶",
            "奸笑",
            "使眼色",
            "wink",
            "teasing",
            "naughty",
            "mischievous",
        ],
        "cool": [
            "酷",
            "帅",
            "厉害",
            "棒极了",
            "真棒",
            "牛逼",
            "强",
            "优秀",
            "杰出",
            "出色",
            "完美",
            "cool",
            "awesome",
            "amazing",
            "great",
            "impressive",
            "perfect",
        ],
        "relaxed": [
            "放松",
            "舒服",
            "惬意",
            "悠闲",
            "轻松",
            "舒适",
            "安逸",
            "自在",
            "relax",
            "relaxed",
            "comfortable",
            "cozy",
            "chill",
            "peaceful",
        ],
        "delicious": [
            "好吃",
            "美味",
            "香",
            "馋",
            "可口",
            "香甜",
            "大餐",
            "大快朵颐",
            "流口水",
            "垂涎",
            "delicious",
            "yummy",
            "tasty",
            "yum",
            "appetizing",
            "mouthwatering",
        ],
        "kissy": [
            "亲亲",
            "么么",
            "吻",
            "mua",
            "muah",
            "亲一下",
            "飞吻",
            "kiss",
            "xoxo",
            "hug",
            "muah",
            "smooch",
        ],
        "confident": [
            "自信",
            "肯定",
            "确定",
            "毫无疑问",
            "当然",
            "必须的",
            "毫无疑问",
            "确信",
            "坚信",
            "confident",
            "sure",
            "certain",
            "definitely",
            "positive",
        ],
        "sleepy": [
            "困",
            "睡觉",
            "晚安",
            "想睡",
            "好累",
            "疲惫",
            "疲倦",
            "困了",
            "想休息",
            "睡意",
            "sleep",
            "sleepy",
            "tired",
            "exhausted",
            "bedtime",
            "good night",
        ],
        "silly": [
            "傻",
            "笨",
            "呆",
            "憨",
            "蠢",
            "二",
            "憨憨",
            "傻乎乎",
            "呆萌",
            "silly",
            "stupid",
            "dumb",
            "foolish",
            "goofy",
            "ridiculous",
        ],
        "confused": [
            "疑惑",
            "不明白",
            "不懂",
            "困惑",
            "疑问",
            "为什么",
            "怎么回事",
            "啥意思",
            "不清楚",
            "confused",
            "puzzled",
            "doubt",
            "question",
            "what",
            "why",
            "how",
        ],
    }

    # 特殊句型判断（中英文）
    # 赞美他人
    if any(
        phrase in text
        for phrase in [
            "你真",
            "你好",
            "您真",
            "你真棒",
            "你好厉害",
            "你太强了",
            "你真好",
            "你真聪明",
            "you are",
            "you're",
            "you look",
            "you seem",
            "so smart",
            "so kind",
        ]
    ):
        return "loving"
    # 自我赞美
    if any(
        phrase in text
        for phrase in [
            "我真",
            "我最",
            "我太棒了",
            "我厉害",
            "我聪明",
            "我优秀",
            "i am",
            "i'm",
            "i feel",
            "so good",
            "so happy",
        ]
    ):
        return "cool"
    # 晚安/睡觉相关
    if any(
        phrase in text
        for phrase in [
            "睡觉",
            "晚安",
            "睡了",
            "好梦",
            "休息了",
            "去睡了",
            "sleep",
            "good night",
            "bedtime",
            "go to bed",
        ]
    ):
        return "sleepy"
    # 疑问句
    if has_question and not has_exclamation:
        return "thinking"
    # 强烈情感（感叹号）
    if has_exclamation and not has_question:
        # 检查是否是积极内容
        positive_words = (
            emotion_keywords["happy"]
            + emotion_keywords["laughing"]
            + emotion_keywords["cool"]
        )
        if any(word in text for word in positive_words):
            return "laughing"
        # 检查是否是消极内容
        negative_words = (
            emotion_keywords["angry"]
            + emotion_keywords["sad"]
            + emotion_keywords["crying"]
        )
        if any(word in text for word in negative_words):
            return "angry"
        return "surprised"
    # 省略号（表示犹豫或思考）
    if has_ellipsis:
        return "thinking"

    # 关键词匹配（带权重）
    emotion_scores = {emotion: 0 for emotion in emoji_map.keys()}

    # 给匹配到的关键词加分
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text:
                emotion_scores[emotion] += 1

    # 给长文本中的重复关键词额外加分
    if len(text) > 20:  # 长文本
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                emotion_scores[emotion] += text.count(keyword) * 0.5

    # 根据分数选择最可能的情感
    max_score = max(emotion_scores.values())
    if max_score == 0:
        return "happy"  # 默认

    # 可能有多个情感同分，根据上下文选择最合适的
    top_emotions = [e for e, s in emotion_scores.items() if s == max_score]

    # 如果多个情感同分，使用以下优先级
    priority_order = [
        "laughing",
        "crying",
        "angry",
        "surprised",
        "shocked",  # 强烈情感优先
        "loving",
        "happy",
        "funny",
        "cool",  # 积极情感
        "sad",
        "embarrassed",
        "confused",  # 消极情感
        "thinking",
        "winking",
        "relaxed",  # 中性情感
        "delicious",
        "kissy",
        "confident",
        "sleepy",
        "silly",  # 特殊场景
    ]

    for emotion in priority_order:
        if emotion in top_emotions:
            return emotion

    return top_emotions[0]  # 如果都不在优先级列表里，返回第一个


def audio_to_data(audio_file_path, is_opus=True):
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

    # 音频时长(秒)
    duration = len(audio) / 1000.0

    # 获取原始PCM数据（16位小端）
    raw_data = audio.raw_data
    return pcm_to_data(raw_data, is_opus), duration


def pcm_to_data(raw_data, is_opus=True):
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
            else:
                filtered[k] = v
        return filtered

    return _filter_dict(copy.deepcopy(config))
