import json
from config.logger import setup_logging
from core.handle.sendAudioHandle import send_stt_message
from core.utils.util import remove_punctuation_and_length
import shutil
import asyncio
import os
import random
import time

TAG = __name__
logger = setup_logging()

WAKEUP_CONFIG = {
    "dir": "config/assets/",
    "file_name": "wakeup_words",
    "create_time": time.time(),
    "refresh_time": 10,
    "words": ["你好小智", "你好啊小智", "小智你好", "小智"],
    "text": "",
}


async def handleHelloMessage(conn):
    await conn.websocket.send(json.dumps(conn.welcome_msg))


async def checkWakeupWords(conn, text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]
    """是否开启唤醒词加速"""
    if not enable_wakeup_words_response_cache:
        return False
    """检查是否是唤醒词"""
    _, text = remove_punctuation_and_length(text)
    if text in conn.config.get("wakeup_words"):
        await send_stt_message(conn, text)
        conn.tts_first_text_index = 0
        conn.tts_last_text_index = 0
        conn.llm_finish_task = True

        file = getWakeupWordFile(WAKEUP_CONFIG["file_name"])
        if file is None:
            asyncio.create_task(wakeupWordsResponse(conn))
            return False
        opus_packets, duration = conn.tts.audio_to_opus_data(file)
        text_hello = WAKEUP_CONFIG["text"]
        if not text_hello:
            text_hello = text
        conn.audio_play_queue.put((opus_packets, text_hello, 0))
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
            logger.bind(tag=TAG).error("连接对象没有llm")
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
