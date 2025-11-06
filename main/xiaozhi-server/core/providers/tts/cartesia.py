"""
Cartesia TTS SDK 实现

使用官方 Cartesia Python SDK 实现流式 TTS
文档: https://docs.cartesia.ai/
"""

import asyncio
import os
import time
from typing import Optional, Callable, Dict, Any
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import InterfaceType

try:
    import cartesia
except ImportError:
    raise ImportError(
        "Cartesia SDK not installed. Install with: pip install cartesia"
    )

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    """
    Cartesia TTS SDK 提供商
    
    特点：
    - 低延迟流式合成
    - 支持多种语言和声音
    - 使用官方 SDK，代码简洁
    
    配置示例:
        CartesiaSDK:
            type: cartesia_sdk
            api_key: your_api_key
            voice_id: your_voice_id  # 或 voice_embedding
            model: sonic-3
            language: en
            encoding: pcm_s16le
            sample_rate: 24000
            output_dir: tmp/
    """
    
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        
        # 标记为单流式接口
        self.interface_type = InterfaceType.SINGLE_STREAM
        # 设置音频文件类型为 WAV
        self.audio_file_type = "wav"
        
        # 获取 API Key
        self.api_key = config.get("api_key") or os.environ.get("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Cartesia API key is required. "
                "Provide via api_key in config or set CARTESIA_API_KEY environment variable"
            )
        
        # Voice 配置（支持 voice_id 或 voice_embedding）
        # 优先读取顶层 voice_id，然后检查嵌套的 voice.id 和 voice.embedding
        self.voice_id = config.get("voice_id", "")
        self.voice_embedding = None
        
        if not self.voice_id:
            voice_config = config.get("voice", {})
            if isinstance(voice_config, dict):
                self.voice_id = voice_config.get("id", "")
                self.voice_embedding = voice_config.get("embedding")
            elif voice_config:  # 如果 voice 是字符串，直接作为 voice_id
                self.voice_id = voice_config
        
        # 模型和语言配置
        self.model = config.get("model", "sonic-3")
        self.language = config.get("language", "en")
        
        # 音频配置
        self.encoding = config.get("encoding", "pcm_s16le")
        # 确保 sample_rate 是整数类型（配置文件可能返回字符串）
        sample_rate_value = config.get("sample_rate", 24000)
        self.sample_rate = int(sample_rate_value) if isinstance(sample_rate_value, str) else sample_rate_value
        
        # 验证至少有一个 voice 配置
        if not self.voice_id and not self.voice_embedding:
            raise ValueError(
                "Voice configuration is required. "
                "Provide either voice_id or voice.embedding in config"
            )
        
        # 初始化 SDK 客户端
        self.client = cartesia.Cartesia(api_key=self.api_key)
        self._ws_client = None
        
        logger.bind(tag=TAG).info(
            f"Cartesia SDK initialized: model={self.model}, "
            f"voice_id={self.voice_id[:8]+'...' if self.voice_id else 'embedding'}, "
            f"language={self.language}, "
            f"encoding={self.encoding}, sample_rate={self.sample_rate}"
        )
    
    async def _get_ws_client(self):
        """获取或创建 WebSocket 客户端（复用连接）"""
        if self._ws_client is None:
            self._ws_client = self.client.tts.websocket()
        return self._ws_client
    
    def _prepare_voice_param(self) -> Dict[str, Any]:
        """准备 voice 参数（避免重复代码）"""
        if self.voice_id:
            return {
                "mode": "id",
                "id": self.voice_id
            }
        elif self.voice_embedding:
            return {
                "mode": "embedding",
                "embedding": self.voice_embedding
            }
        else:
            raise ValueError("Neither voice_id nor voice_embedding is configured")
    
    async def text_to_speak(self, text: str, output_file: Optional[str] = None) -> Optional[bytes]:
        """
        将文本转换为 WAV 格式音频（完整音频，非流式）
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径（未使用，保留兼容性）
            
        Returns:
            WAV 格式的完整音频字节数据
        """
        import io
        import wave
        
        try:
            ws = await self._get_ws_client()
            
            pcm_chunks = []
            voice = self._prepare_voice_param()
            
            # 发送流式请求，获取 PCM 数据
            for output in ws.send(
                model_id=self.model,
                transcript=text,
                voice=voice,
                stream=True,
                output_format={
                    "container": "raw",
                    "encoding": self.encoding,  # pcm_s16le
                    "sample_rate": self.sample_rate  # 16000 or 24000
                }
            ):
                # Cartesia SDK 返回 WebSocketTtsOutput 对象
                # 从 output.audio 获取 PCM 音频数据
                if output and hasattr(output, 'audio') and output.audio:
                    pcm_chunks.append(output.audio)
            
            # 合并所有 PCM 音频块
            pcm_data = b''.join(pcm_chunks)
            
            # 将 PCM 转换为 WAV 格式
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.sample_rate)  # 使用配置的采样率
                wav_file.writeframes(pcm_data)
            
            wav_bytes = wav_buffer.getvalue()
            
            # 返回完整的 WAV 字节数据
            return wav_bytes
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Cartesia TTS failed: {e}", exc_info=True)
            raise
    
    async def close(self):
        """关闭 WebSocket 连接（Cartesia SDK 会自动管理）"""
        self._ws_client = None

