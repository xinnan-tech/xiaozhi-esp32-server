import os
import uuid
import edge_tts
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

TAG = __name__

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("format", "mp3")

    async def text_to_speak(self, text, output_file):
        try:
            # Detect if text contains Chinese but voice is English-based
            # Regular expression for CJK characters
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
            
            target_voice = self.voice
            if has_chinese and not any(v in self.voice.lower() for v in ["chinese", "mandarin", "zh-cn"]):
                from config.logger import setup_logging
                logger = setup_logging()
                logger.bind(tag=TAG).info(f"Detected Chinese content with English voice {self.voice}, using fallback zh-CN-XiaoxiaoNeural")
                target_voice = "zh-CN-XiaoxiaoNeural"
            
            return await self._do_communicate(text, target_voice, output_file)
        except Exception as e:
            # General fallback for generic failure
            fallback_voice = "en-US-AndrewMultilingualNeural"
            if self.voice == fallback_voice:
                raise e
                
            from config.logger import setup_logging
            logger = setup_logging()
            logger.bind(tag=TAG).warning(f"Edge TTS failed with {target_voice if 'target_voice' in locals() else self.voice}, trying fallback {fallback_voice}: {e}")
            try:
                return await self._do_communicate(text, fallback_voice, output_file)
            except Exception as e2:
                error_msg = f"Edge TTS fallback failed: {e2}"
                raise Exception(error_msg)

    async def _do_communicate(self, text, voice, output_file):
        communicate = edge_tts.Communicate(text, voice=voice)
        if output_file:
            # 确保目录存在并创建空文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as f:
                pass

            # 流式写入音频数据
            with open(output_file, "ab") as f:  # 改为追加模式避免覆盖
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":  # 只处理音频数据块
                        f.write(chunk["data"])
            return True
        else:
            # 返回音频二进制数据
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            return audio_bytes