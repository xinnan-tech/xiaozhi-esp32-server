import time
import json
import uuid
import random
import asyncio
from typing import TYPE_CHECKING
from config.logger import setup_logging

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.dialogue import Message
from core.utils.util import audio_to_data, audio_file_to_wav_bytes
from core.providers.tts.dto.dto import SentenceType
from core.utils.wakeup_word import WakeupWordsConfig
from core.handle.sendAudioHandle import sendAudioMessage, send_tts_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)

TAG = __name__
_wakeup_logger = setup_logging()

WAKEUP_CONFIG = {
    "refresh_time": 10,
    "responses": [
        "我一直都在呢，您请说。",
        "在的呢，请随时吩咐我。",
        "来啦来啦，请告诉我吧。",
        "您请说，我正听着。",
        "请您讲话，我准备好了。",
        "请您说出指令吧。",
        "我认真听着呢，请讲。",
        "请问您需要什么帮助？",
        "我在这里，等候您的指令。",
    ],
}

# 创建全局的唤醒词配置管理器
wakeup_words_config = WakeupWordsConfig()

# 用于防止并发调用wakeupWordsResponse的锁
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn: "ConnectionHandler", msg_json):
    """处理hello消息"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).debug(f"客户端音频格式: {format}")
        conn.audio_format = format
        conn.welcome_msg["audio_params"] = audio_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).debug(f"客户端特性: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).debug("客户端支持MCP")
            conn.mcp_client = MCPClient()
        if features.get("aec"):
            conn.logger.bind(tag=TAG).debug("客户端启用了服务端AEC")
            conn.client_aec = True

    await conn.websocket.send(json.dumps(conn.welcome_msg))

    # The device waits for the server hello before processing MCP messages.
    if features and features.get("mcp"):
        asyncio.create_task(send_mcp_initialize_message(conn))
        # 并发预发 tools/list，让帧排在 audio 流之前到达 client
        asyncio.create_task(send_mcp_tools_list_request(conn))


async def checkWakeupWords(conn: "ConnectionHandler", text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]

    # 等待tts初始化，最多等待3秒
    start_time = time.time()
    while time.time() - start_time < 3:
        if conn.tts:
            break
        await asyncio.sleep(0.1)
    else:
        return False

    if not enable_wakeup_words_response_cache:
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text not in conn.config.get("wakeup_words"):
        return False

    conn.just_woken_up = True
    await send_tts_message(conn, "start")

    # 获取当前音色
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # 获取唤醒词回复配置
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words_short.wav",
            "time": 0,
            "text": "我在这里哦！",
        }

    # 获取音频数据
    opus_packets = await audio_to_data(response.get("file_path"), use_cache=True)
    # 播放唤醒词回复
    conn.client_abort = False

    # 将唤醒词回复视为新会话，生成新的 sentence_id，确保流控器重置
    conn.sentence_id = str(uuid.uuid4().hex)

    # 补充对话
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))
    conn.logger.bind(tag=TAG).info(f"播放唤醒词回复: {response.get('text')}")

    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    asyncio.create_task(_finish_wakeup_reply(conn))

    # 检查是否需要更新唤醒词回复
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def _finish_wakeup_reply(conn: "ConnectionHandler"):
    """等音频队列清空后再发 stop（时序：全部音频帧→stop），期间不阻塞接收循环"""
    try:
        await sendAudioMessage(conn, SentenceType.LAST, [], None)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"唤醒词回复收尾失败: {e}")


async def wakeupWordsResponse(conn: "ConnectionHandler"):
    if not conn.tts:
        return

    try:
        # 尝试获取锁，如果获取不到就返回
        if not await _wakeup_response_lock.acquire():
            return

        # 从预定义回复列表中随机选择一个回复
        result = random.choice(WAKEUP_CONFIG["responses"])
        if not result or len(result) == 0:
            return

        # 生成TTS音频
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # 获取当前音色
        voice = getattr(conn.tts, "voice", "default")

        # 保留的 TTS 音频是文件路径而非 Opus 帧：直接转目标采样率 wav，跳过有损 Opus 往返
        if isinstance(tts_result, str):
            wav_bytes = await asyncio.to_thread(
                audio_file_to_wav_bytes, tts_result, conn.sample_rate
            )
        else:
            wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=conn.sample_rate)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # 更新配置
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
        # 覆写文件后 mtime 变化使旧缓存失效，此处立刻预编码新文件，
        # 下次唤醒直接命中缓存，编码成本不占用唤醒响应路径
        await audio_to_data(file_path, use_cache=True)
    finally:
        # 确保在任何情况下都释放锁
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()


async def preheat_wakeup_audio_cache():
    """进程启动时预热唤醒词音频编码缓存

    把 wakeup_words/{voice}.wav 在 Opus 编码结果一次性算好塞进全局 cache，
    后续每条连接上来就能直接命中，省掉 wav→PCM→Opus 的数百毫秒开销。
    """
    # 进程启动时 tts 还未初始化，无法拿到 conn.tts.voice，按常见 fallback 列表预热
    preheat_voices = ["default", "female-shaonv", "male-qn-jingying"]
    fallback_path = "config/assets/wakeup_words_short.wav"
    for voice in preheat_voices:
        file_path = fallback_path
        try:
            response = wakeup_words_config.get_wakeup_response(voice)
            if response and response.get("file_path"):
                file_path = response["file_path"]
            await audio_to_data(file_path, use_cache=True)
        except Exception as e:
            _wakeup_logger.bind(tag=TAG).warning(
                f"预热 voice={voice} 失败: {e}"
            )
