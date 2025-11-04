"""
ElevenLabs TTS SDK 实现

使用官方 ElevenLabs Python SDK 实现流式 TTS
文档: https://elevenlabs.io/docs/
"""

import asyncio
import os
from typing import Optional, Callable
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import InterfaceType
from core.utils import opus_encoder_utils

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
except ImportError:
    raise ImportError(
        "ElevenLabs SDK not installed. Install with: pip install elevenlabs"
    )

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    """
    ElevenLabs TTS SDK 提供商
    
    特点：
    - 高质量、情感丰富的语音
    - 支持声音克隆
    - 使用官方 SDK，代码简洁
    
    配置示例:
        ElevenLabsSDK:
            type: elevenlabs_sdk
            api_key: your_api_key
            voice_id: 21m00Tcm4TlvDq8ikWAM  # Rachel voice
            model: eleven_multilingual_v2
            output_format: pcm_16000
            stability: 0.5
            similarity_boost: 0.75
            style: 0.0
            use_speaker_boost: true
            output_dir: tmp/
    """
    
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        
        # 标记为单流式接口
        self.interface_type = InterfaceType.SINGLE_STREAM
        
        # 获取 API Key
        self.api_key = config.get("api_key") or os.environ.get("ELEVEN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key is required. "
                "Provide via api_key in config or set ELEVEN_API_KEY environment variable"
            )
        
        # Voice 配置
        self.voice_id = config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel (default)
        
        # 模型配置
        self.model = config.get("model", "eleven_multilingual_v2")
        
        # 音频输出格式
        self.output_format = config.get("output_format", "pcm_16000")
        
        # Voice Settings
        self.stability = config.get("stability", 0.5)
        self.similarity_boost = config.get("similarity_boost", 0.75)
        self.style = config.get("style", 0.0)
        self.use_speaker_boost = config.get("use_speaker_boost", True)
        
        # 流式延迟优化 (0-4，越大延迟越低但质量可能下降，推荐 2-3)
        self.optimize_streaming_latency = config.get("optimize_streaming_latency", 3)
        
        # 初始化 SDK 客户端
        self.client = ElevenLabs(api_key=self.api_key)
        
        # 创建 VoiceSettings
        self.voice_settings = VoiceSettings(
            stability=self.stability,
            similarity_boost=self.similarity_boost,
            style=self.style,
            use_speaker_boost=self.use_speaker_boost
        )
        
        # 初始化 Opus 编码器（ElevenLabs pcm_16000 是 16kHz PCM）
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
        
        # PCM 缓冲区（用于累积不完整的帧）
        self.pcm_buffer = bytearray()
        
        logger.bind(tag=TAG).info(
            f"ElevenLabs SDK initialized: model={self.model}, "
            f"voice_id={self.voice_id[:8]}..., "
            f"format={self.output_format}"
        )
    
    async def text_to_speak(self, text: str, output_file: Optional[str] = None) -> Optional[bytes]:
        """
        非流式方法：将完整文本转换为音频
        
        注意：此方法会等待完整音频生成
        建议使用 to_tts_stream() 方法以获得更低的延迟
        """
        try:
            # 使用 SDK 的 convert 方法生成完整音频
            audio_data = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model,
                output_format=self.output_format,
                voice_settings=self.voice_settings
            )
            
            # 保存到文件或返回
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(audio_data)
                logger.bind(tag=TAG).info(f"Audio saved to {output_file}, size: {len(audio_data)} bytes")
                return None
            else:
                return audio_data
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"ElevenLabs TTS failed: {e}", exc_info=True)
            raise
    
    def to_tts_stream(self, text: str, opus_handler: Optional[Callable] = None):
        """
        流式生成音频（核心方法）
        
        注意：浏览器端使用 Web Audio API 播放，直接发送 PCM 数据
        ESP32 等嵌入式设备使用 Opus，需要编码
        
        Args:
            text: 要合成的文本
            opus_handler: 音频数据回调函数 (接收 bytes)
        """
        import time
        try:
            from core.providers.tts.dto.dto import SentenceType
            
            start_time = time.time()
            text_preview = text[:30] + "..." if len(text) > 30 else text
            logger.bind(tag=TAG).info(f"🎙️ TTS开始: [{text_preview}]")
            
            # 发送句子开始标记
            self.tts_audio_queue.put((SentenceType.FIRST, None, text))
            
            # 使用 SDK 的 stream 方法（返回 Iterator[bytes] PCM 数据）
            audio_stream = self.client.text_to_speech.stream(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model,
                output_format=self.output_format,
                voice_settings=self.voice_settings,
                optimize_streaming_latency=self.optimize_streaming_latency
            )
            
            first_chunk_time = None
            chunk_count = 0
            
            # 直接发送 PCM 数据（浏览器端可以直接播放）
            for pcm_chunk in audio_stream:
                if pcm_chunk and opus_handler:
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        ttfb = (first_chunk_time - start_time) * 1000
                        logger.bind(tag=TAG).info(f"⚡ 首包延迟: {ttfb:.0f}ms")
                    chunk_count += 1
                    opus_handler(pcm_chunk)
            
            # 发送句子结束标记
            self.tts_audio_queue.put((SentenceType.LAST, None, text))
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            logger.bind(tag=TAG).info(
                f"✅ TTS完成: {chunk_count}块, 耗时 {total_time:.0f}ms"
            )
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS 合成失败: {e}", exc_info=True)
            raise
    
    async def close(self):
        """清理资源（ElevenLabs SDK 自动管理连接）"""
        pass

