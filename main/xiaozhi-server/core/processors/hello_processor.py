import time
import json
import random
import asyncio
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.dialogue import Message
from core.utils.util import audio_to_data, remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tts.dto.dto import SentenceType
from core.utils.wakeup_word import WakeupWordsConfig
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)
from config.logger import setup_logging

logger = setup_logging()

# 唤醒词配置
WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["你好", "你好啊", "嘿，你好", "嗨"],
}

# 创建全局的唤醒词配置管理器
wakeup_words_config = WakeupWordsConfig()

# 用于防止并发调用wakeupWordsResponse的锁
_wakeup_response_lock = asyncio.Lock()


class HelloProcessor(MessageProcessor):
    """Hello消息处理器：完整迁移helloHandle.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理hello类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "hello":
                    await self.handle_hello_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_hello_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理hello消息 - 完整迁移自handleHelloMessage"""
        # 处理音频参数
        audio_params = msg_json.get("audio_params")
        if audio_params:
            format = audio_params.get("format")
            logger.info(f"客户端音频格式: {format}")
            context.audio_format = format
            if not context.welcome_msg:
                context.welcome_msg = {}
            context.welcome_msg["audio_params"] = audio_params
            
        # 处理客户端特性
        features = msg_json.get("features")
        if features:
            logger.info(f"客户端特性: {features}")
            context.features = features
            if features.get("mcp"):
                logger.info("客户端支持MCP")
                context.mcp_client = MCPClient()
                # 发送初始化 - 传递transport参数
                asyncio.create_task(send_mcp_initialize_message(context, transport))
                # 发送mcp消息，获取tools列表 - 传递transport参数
                asyncio.create_task(send_mcp_tools_list_request(context, transport))

        # 发送欢迎消息
        if context.welcome_msg:
            await transport.send(json.dumps(context.welcome_msg))
        else:
            # 默认欢迎消息
            welcome_msg = {
                "type": "hello",
                "session_id": context.session_id,
                "version": 1,
                "transport": "websocket"
            }
            await transport.send(json.dumps(welcome_msg))
    
    async def check_wakeup_words(self, context: SessionContext, transport: TransportInterface, text: str) -> bool:
        """检查唤醒词 - 完整迁移自checkWakeupWords"""
        enable_wakeup_words_response_cache = context.config.get("enable_wakeup_words_response_cache", False)

        # 等待tts初始化，最多等待3秒
        tts_component = context.components.get('tts')
        start_time = time.time()
        while time.time() - start_time < 3:
            if tts_component and hasattr(tts_component, 'tts_instance'):
                break
            await asyncio.sleep(0.1)
        else:
            return False

        if not enable_wakeup_words_response_cache:
            return False

        _, filtered_text = remove_punctuation_and_length(text)
        if filtered_text not in context.config.get("wakeup_words", []):
            return False

        context.just_woken_up = True
        await self._send_stt_message(context, transport, text)

        # 获取当前音色
        tts_instance = getattr(tts_component, 'tts_instance', None) if tts_component else None
        voice = getattr(tts_instance, "voice", "default") if tts_instance else "default"
        if not voice:
            voice = "default"

        # 获取唤醒词回复配置
        response = wakeup_words_config.get_wakeup_response(voice)
        if not response or not response.get("file_path"):
            response = {
                "voice": "default",
                "file_path": "config/assets/wakeup_words.wav",
                "time": 0,
                "text": "哈啰啊，我是小智啦，声音好听的台湾女孩一枚，超开心认识你耶，最近在忙啥，别忘了给我来点有趣的料哦，我超爱听八卦的啦",
            }

        # 获取音频数据
        opus_packets = audio_to_data(response.get("file_path"))
        # 播放唤醒词回复
        context.abort_requested = False

        logger.info(f"播放唤醒词回复: {response.get('text')}")
        await self._send_audio_message(context, transport, SentenceType.FIRST, opus_packets, response.get("text"))
        await self._send_audio_message(context, transport, SentenceType.LAST, [], None)

        # 补充对话
        if context.dialogue:
            context.dialogue.put(Message(role="assistant", content=response.get("text")))

        # 检查是否需要更新唤醒词回复
        if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
            if not _wakeup_response_lock.locked():
                asyncio.create_task(self._wakeup_words_response(context, transport))
        return True

    async def _wakeup_words_response(self, context: SessionContext, transport: TransportInterface):
        """生成唤醒词回复 - 完整迁移自wakeupWordsResponse"""
        tts_component = context.components.get('tts')
        llm_component = context.components.get('llm')
        
        tts_instance = getattr(tts_component, 'tts_instance', None) if tts_component else None
        llm_instance = getattr(llm_component, 'llm_instance', None) if llm_component else None
        
        if not tts_instance or not llm_instance or not hasattr(llm_instance, 'response_no_stream'):
            return

        try:
            # 尝试获取锁，如果获取不到就返回
            async with _wakeup_response_lock:
                # 生成唤醒词回复
                wakeup_word = random.choice(WAKEUP_CONFIG["words"])
                question = (
                    "此刻用户正在和你说```"
                    + wakeup_word
                    + "```。\n请你根据以上用户的内容进行20-30字回复。要符合系统设置的角色情感和态度，不要像机器人一样说话。\n"
                    + "请勿对这条内容本身进行任何解释和回应，请勿返回表情符号，仅返回对用户的内容的回复。"
                )

                result = llm_instance.response_no_stream(context.config.get("prompt", ""), question)
                if not result or len(result) == 0:
                    return

                # 生成TTS音频
                tts_result = await asyncio.to_thread(tts_instance.to_tts, result)
                if not tts_result:
                    return

                # 获取当前音色
                voice = getattr(tts_instance, "voice", "default")

                wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
                file_path = wakeup_words_config.generate_file_path(voice)
                with open(file_path, "wb") as f:
                    f.write(wav_bytes)
                # 更新配置
                wakeup_words_config.update_wakeup_response(voice, file_path, result)
        except Exception as e:
            logger.error(f"生成唤醒词回复失败: {e}")

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        await transport.send(json.dumps({
            "type": "stt",
            "text": text,
            "session_id": context.session_id
        }))

    async def _send_audio_message(self, context: SessionContext, transport: TransportInterface, 
                                 sentence_type: SentenceType, audios: bytes, text: str):
        """发送音频消息"""
        # 这里应该调用AudioSendProcessor
        from core.processors.audio_send_processor import AudioSendProcessor
        audio_send_processor = AudioSendProcessor()
        await audio_send_processor.send_audio_message(context, transport, sentence_type, audios, text)

