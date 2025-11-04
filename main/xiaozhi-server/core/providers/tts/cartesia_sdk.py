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
            model: sonic-english
            language: en
            encoding: pcm_s16le
            sample_rate: 24000
            output_dir: tmp/
    """
    
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        
        # 标记为单流式接口
        self.interface_type = InterfaceType.SINGLE_STREAM
        
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
        self.model = config.get("model", "sonic-english")
        self.language = config.get("language", "en")
        
        # 音频配置
        self.encoding = config.get("encoding", "pcm_s16le")
        self.sample_rate = config.get("sample_rate", 24000)
        
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
        非流式方法：将完整文本转换为音频
        
        注意：Cartesia 主要设计为流式使用，此方法会等待完整音频生成
        建议使用 to_tts_stream() 方法以获得更低的延迟
        """
        try:
            ws = await self._get_ws_client()
            
            audio_chunks = []
            voice = self._prepare_voice_param()
            
            # 发送流式请求
            for output in ws.send(
                model_id=self.model,
                transcript=text,
                voice=voice,
                stream=True,
                output_format={
                    "container": "raw",
                    "encoding": self.encoding,
                    "sample_rate": self.sample_rate
                }
            ):
                # Cartesia SDK 返回 WebSocketTtsOutput 对象
                # 从 output.audio 获取音频数据
                if output and hasattr(output, 'audio') and output.audio:
                    audio_chunks.append(output.audio)
            
            # 合并所有音频块
            audio_data = b''.join(audio_chunks)
            
            # 保存到文件或返回
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(audio_data)
                logger.bind(tag=TAG).info(f"Audio saved to {output_file}, size: {len(audio_data)} bytes")
                return None
            else:
                return audio_data
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Cartesia TTS failed: {e}", exc_info=True)
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
        try:
            from core.providers.tts.dto.dto import SentenceType
            
            start_time = time.time()
            text_preview = text[:30] + "..." if len(text) > 30 else text
            logger.bind(tag=TAG).info(f"🎙️ TTS开始: [{text_preview}]")
            
            # 发送句子开始标记
            self.tts_audio_queue.put((SentenceType.FIRST, None, text))
            
            # 在异步事件循环中运行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 运行异步合成
                chunk_count = loop.run_until_complete(
                    self._stream_synthesis(text, opus_handler, start_time)
                )
            finally:
                loop.close()
            
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
    
    async def _stream_synthesis(self, text: str, opus_handler: Optional[Callable], start_time: float) -> int:
        """
        异步流式合成实现
        
        Args:
            text: 要合成的文本
            opus_handler: 音频数据回调函数
            start_time: 开始时间（用于计算首包延迟）
            
        Returns:
            生成的音频块数量
        """
        try:
            ws = await self._get_ws_client()
            voice = self._prepare_voice_param()
            
            first_chunk_time = None
            chunk_count = 0
            
            # 发送流式请求并处理响应
            for output in ws.send(
                model_id=self.model,
                transcript=text,
                voice=voice,
                stream=True,
                output_format={
                    "container": "raw",
                    "encoding": self.encoding,
                    "sample_rate": self.sample_rate
                },
                language=self.language
            ):
                # Cartesia SDK 返回 WebSocketTtsOutput 对象
                # 需要从 output.audio 获取实际的音频数据
                if output and hasattr(output, 'audio'):
                    audio_data = output.audio
                    
                    if audio_data:
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            ttfb = (first_chunk_time - start_time) * 1000
                            logger.bind(tag=TAG).info(f"⚡ 首包延迟: {ttfb:.0f}ms")
                        
                        # 发送音频数据（bytes）
                        if opus_handler:
                            opus_handler(audio_data)
                            chunk_count += 1
            
            return chunk_count
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Stream synthesis error: {e}", exc_info=True)
            raise
    
    async def close(self):
        """关闭 WebSocket 连接（Cartesia SDK 会自动管理）"""
        self._ws_client = None

