import time
import numpy as np
import torch
import opuslib_next
import openai  # 新增OpenAI库导入
from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase
from core.utils.util import create_instance

TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    def __init__(self, config):
        logger.bind(tag=TAG).info("VAD_volcengine", config)
        self.base_vad_model = create_instance("silero", config)
        
        # 处理空字符串的情况
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")
        max_silence_duration_ms = config.get("min_silence_duration_ms", "1000")

        self.semantic_only = config.get("semantic_only", False)
        self.min_silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )
        self.max_silence_threshold_ms = (
            int(max_silence_duration_ms) if max_silence_duration_ms else 3000
        )
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"

        self.base_url = f"https://{self.host}/v1"

    def is_vad(self, conn, opus_packet):
        if self.semantic_only:
            return True
        return self.base_vad_model.is_vad(conn, opus_packet)
     

    def is_eou(self, conn, text) :
        embedding = self._get_embedding(text)
        is_stop = embedding[1] > 0.5
        logger.bind(tag=TAG).info( f"EOU Result: text:{text} embedding:{embedding} stop:{is_stop}")
        if self.semantic_only:
             return is_stop
        silence_duration = self.get_silence_duration(conn)
        if silence_duration <= self.min_silence_threshold_ms:
            # vad 静默时间比较短，倾向于对话未结束，语义判停阈值较高
            return embedding[1] > 0.9
        elif silence_duration > self.min_silence_threshold_ms and silence_duration < self.max_silence_threshold_ms:
            # vad 静默时间比较短，倾向于对话未结束，语义判停阈值较低
            return embedding[1] > 0.6
        else:
            # vad 静默时间比较长，直接判停
            return True
        
       
    
    def get_silence_duration(self, conn) :
        return self.base_vad_model.get_silence_duration(conn)
    
    # 新增嵌入模型调用方法
    def _get_embedding(self, text: str) -> list:
        """调用OpenAI嵌入模型获取文本嵌入向量
        
        Args:
            text: 需要生成嵌入的文本
        
        Returns:
            list: 嵌入向量列表，第一个参数表示未结束的概率
        """
        try:
            client = openai.OpenAI(
                base_url = self.base_url,
                api_key = self.api_key
            )
            response = client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return response["data"][0]["embedding"]
        except Exception as e:
            logger.bind(tag=TAG).error(f"调用嵌入模型失败: {str(e)}")
            raise
    
    
          
