import os
import time
import json
import random
import shutil
import asyncio
from core.handle.sendAudioHandle import send_stt_message
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import ContentType, InterfaceType


TAG = __name__

WAKEUP_CONFIG = {
    "dir": "config/assets/",
    "file_name": "wakeup_words",
    "create_time": time.time(),
    "refresh_time": 10,
    "words": ["你好小智", "你好啊小智", "小智你好", "小智"],
    "text": "",
}


async def handleHelloMessage(conn, msg_json):
    """处理hello消息"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).info(f"客户端音频格式: {format}")
        conn.audio_format = format
        if conn.asr is not None:
            conn.asr.set_audio_format(format)
        conn.welcome_msg["audio_params"] = audio_params

    await conn.websocket.send(json.dumps(conn.welcome_msg))


async def checkWakeupWords(conn, text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]
    """是否用的是非流式tts"""
    if conn.tts and conn.tts.interface_type != InterfaceType.NON_STREAM:
        return False

    """是否开启唤醒词加速"""
    if not enable_wakeup_words_response_cache:
        return False
    """检查是否是唤醒词"""
    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text in conn.config.get("wakeup_words"):
        await send_stt_message(conn, text)

        file = getWakeupWordFile(WAKEUP_CONFIG["file_name"])
        if file is None:
            asyncio.create_task(wakeupWordsResponse(conn))
            return False
        text_hello = WAKEUP_CONFIG["text"]
        if not text_hello:
            text_hello = text
        conn.tts.tts_one_sentence(
            conn, ContentType.FILE, content_file=file, content_detail=text_hello
        )
        if time.time() - WAKEUP_CONFIG["create_time"] > WAKEUP_CONFIG["refresh_time"]:
            asyncio.create_task(wakeupWordsResponse(conn))
        return True
    return False


def getWakeupWordFile(file_name):
    for file in os.listdir(WAKEUP_CONFIG["dir"]):
        if file.startswith("my_" + file_name):
            """避免缓存文件是一个空文件"""
            if os.stat(f"config/assets/{file}").st_size > (15 * 1024):
                return f"config/assets/{file}"

    """查找config/assets/目录下名称为wakeup_words的文件"""
    for file in os.listdir(WAKEUP_CONFIG["dir"]):
        if file.startswith(file_name):
            return f"config/assets/{file}"
    return None


async def wakeupWordsResponse(conn):
    wait_max_time = 5
    while conn.llm is None or not conn.llm.response_no_stream:
        await asyncio.sleep(1)
        wait_max_time -= 1
        if wait_max_time <= 0:
            conn.logger.bind(tag=TAG).error("连接对象没有llm")
            return

    """唤醒词响应"""
    wakeup_word = random.choice(WAKEUP_CONFIG["words"])
    result = conn.llm.response_no_stream(conn.config["prompt"], wakeup_word)
    if result is None or result == "":
        return
    tts_file = await asyncio.to_thread(conn.tts.to_tts, result)

    if tts_file is not None and os.path.exists(tts_file):
        file_type = os.path.splitext(tts_file)[1]
        if file_type:
            file_type = file_type.lstrip(".")
        old_file = getWakeupWordFile("my_" + WAKEUP_CONFIG["file_name"])
        if old_file is not None:
            os.remove(old_file)
        """将文件挪到"wakeup_words.mp3"""
        shutil.move(
            tts_file,
            WAKEUP_CONFIG["dir"] + "my_" + WAKEUP_CONFIG["file_name"] + "." + file_type,
        )
        WAKEUP_CONFIG["create_time"] = time.time()
        WAKEUP_CONFIG["text"] = result
