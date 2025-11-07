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
        # 设置音频文件类型为 MP3
        self.audio_file_type = "pcm"
        
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
        
        logger.bind(tag=TAG).info(
            f"ElevenLabs SDK initialized: model={self.model}, "
            f"voice_id={self.voice_id[:8]}..., "
            f"format=mp3_44100"
        )
    
    async def text_to_speak(self, text: str, output_file: Optional[str] = None) -> Optional[bytes]:
        """
        将文本转换为 MP3 格式音频（完整音频，非流式）
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径（未使用，保留兼容性）
            
        Returns:
            MP3 格式的完整音频字节数据
        """
        try:
            # 使用 SDK 的 convert 方法生成完整音频（返回 generator）
            # 强制使用 mp3_44100 格式（忽略配置中的 output_format）
            # 因为 base.py 需要完整的音频文件格式（MP3/WAV），而不是原始 PCM
            audio_stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model,
                output_format=self.output_format,
                voice_settings=self.voice_settings
            )
            
            # 检查返回类型
            if output_file:
                with open(output_file, 'wb') as f:
                    for chunk in audio_stream:
                        f.write(chunk)
            else:
                audio_bytes = b""
                for chunk in audio_stream:
                    audio_bytes += chunk["data"]
                return audio_bytes
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"ElevenLabs TTS failed: {e}", exc_info=True)
            raise
    
    async def close(self):
        """清理资源（ElevenLabs SDK 自动管理连接）"""
        pass

