import os
import json
import asyncio
import tempfile
import difflib
from typing import Optional, Tuple, List
import dashscope
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

tag = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        """Qwen3-ASR-Flash ASR初始化"""
        
        # 配置参数
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Qwen3-ASR-Flash 需要配置 api_key")
            
        self.model_name = config.get("model_name", "qwen3-asr-flash")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file
        
        # ASR选项配置
        self.enable_lid = config.get("enable_lid", True)  # 自动语种检测
        self.enable_itn = config.get("enable_itn", True)  # 逆文本归一化
        self.language = config.get("language", None)  # 指定语种，默认自动检测
        self.context = config.get("context", "")  # 上下文信息，用于提高识别准确率
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def _prepare_audio_file(self, pcm_data: bytes) -> str:
        """将PCM数据转换为WAV文件并返回文件路径"""
        try:
            import wave
            
            # 创建临时WAV文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            # 写入WAV格式
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)      # 单声道
                wav_file.setsampwidth(2)      # 16位
                wav_file.setframerate(16000)  # 16kHz采样率
                wav_file.writeframes(pcm_data)
                
            return temp_path
            
        except Exception as e:
            logger.bind(tag=tag).error(f"音频文件准备失败: {e}")
            return None

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        temp_file_path = None
        file_path = None
        
        try:
            # 解码音频数据
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            
            combined_pcm_data = b"".join(pcm_data)
            if len(combined_pcm_data) == 0:
                logger.bind(tag=tag).warning("音频数据为空")
                return "", None
            
            # 准备音频文件
            temp_file_path = self._prepare_audio_file(combined_pcm_data)
            if not temp_file_path:
                return "", None
            
            # 保存音频文件（如果需要）
            if not self.delete_audio_file:
                file_path = self.save_audio_to_file(pcm_data, session_id)
            
            # 构造请求消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"audio": temp_file_path}
                    ]
                }
            ]
            
            # 如果有上下文信息，添加system消息
            if self.context:
                messages.insert(0, {
                    "role": "system", 
                    "content": [
                        {"text": self.context}
                    ]
                })
            
            # 准备ASR选项
            asr_options = {
                "enable_lid": self.enable_lid,
                "enable_itn": self.enable_itn
            }
            
            # 如果指定了语种，添加到选项中
            if self.language:
                asr_options["language"] = self.language
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            # 发送流式请求
            response = dashscope.MultiModalConversation.call(
                model=self.model_name,
                messages=messages,
                result_format="message",
                asr_options=asr_options,
                stream=True
            )
            
            # 处理流式响应
            full_text = ""
            last_text = ""  # 用于存储上一个文本片段
            for chunk in response:
                try:
                    text = chunk["output"]["choices"][0]["message"].content[0]["text"]
                    # 标准化文本片段（去除首尾空格）
                    normalized_text = text.strip()
                    # 只有当新文本片段与上一个不同时才处理
                    if normalized_text != last_text:
                        # 提取新增的文本部分
                        # 通过比较当前文本和上一个文本，找到新增的部分
                        if normalized_text.startswith(last_text):
                            # 如果当前文本以最后一个文本开头，则新增部分是两者的差集
                            new_part = normalized_text[len(last_text):]
                        else:
                            # 如果不以最后一个文本开头，说明识别结果发生了较大变化，直接使用当前文本
                            new_part = normalized_text
                        
                        # 将新增部分添加到完整文本中
                        full_text += new_part
                        last_text = normalized_text
                    # 这里可以实时处理文本片段，例如通过回调函数
                except:
                    pass
            
            return full_text, file_path
                
        except Exception as e:
            logger.bind(tag=tag).error(f"语音识别失败: {e}")
            return "", file_path
            
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.bind(tag=tag).warning(f"清理临时文件失败: {e}")