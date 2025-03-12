import os
import uuid
import requests
from config.logger import setup_logging
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        # POST请求地址
        self.url = config.get("url")
        # 从配置中加载所有参数
        self.app_key = config.get("app_key")
        self.audio_dl_url = config.get("audio_dl_url")
        self.model_name = config.get("model_name")
        self.speaker_name = config.get("speaker_name")
        self.prompt_text_lang = config.get("prompt_text_lang")
        self.emotion = config.get("emotion")
        self.text_lang = config.get("text_lang")
        self.top_k = config.get("top_k")
        self.top_p = config.get("top_p")
        self.temperature = config.get("temperature")
        self.text_split_method = config.get("text_split_method")
        self.batch_size = config.get("batch_size")
        self.batch_threshold = config.get("batch_size")
        self.split_bucket = config.get("split_bucket")
        self.speed_facter = config.get("speed_facter")
        self.fragment_interval = config.get("fragment_interval")
        self.media_type = config.get("media_type")
        self.parallel_infer = config.get("parallel_infer")
        self.repetition_penalty = config.get("repetition_penalty")
        self.seed = config.get("seed")

    def generate_filename(self):
        """根据媒体类型生成文件名"""
        extension = f".{self.media_type}"
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}"
        )

    async def text_to_speak(self, text, output_file):
        """文本转语音并保存音频文件"""
        # 构造请求体
        request_body = {
            "app_key": self.app_key,
            "audio_dl_url": self.audio_dl_url,
            "model_name": self.model_name,
            "speaker_name": self.speaker_name,
            "prompt_text_lang": self.prompt_text_lang,
            "emotion": self.emotion,
            "text": text,
            "text_lang": self.text_lang,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "text_split_method": self.text_split_method,
            "batch_size": self.batch_size,
            "batch_threshold": self.batch_threshold,
            "split_bucket": self.split_bucket,
            "speed_facter": self.speed_facter,
            "fragment_interval": self.fragment_interval,
            "media_type": self.media_type,
            "parallel_infer": self.parallel_infer,
            "repetition_penalty": self.repetition_penalty,
            "seed": self.seed
        }

        body = {
            "app_key": "",
            "audio_dl_url": "http://127.0.0.1:9881",
            "model_name": "【原神】须弥",
            "speaker_name": "纳西妲",
            "prompt_text_lang": "中文",
            "emotion": "中立_neutral",
            "text": text,
            "text_lang": "中文",
            "top_k": 10,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "按标点符号切",
            "batch_size": 10,
            "batch_threshold": 0.75,
            "split_bucket": True,
            "speed_facter": 1,
            "fragment_interval": 0.3,
            "media_type": "wav",
            "parallel_infer": True,
            "repetition_penalty": 1.35,
            "seed": -1
        }

        try:
            # 发送POST请求
            resp = requests.post(self.url, json=body)
            resp.raise_for_status()
            
            # 解析响应
            result = resp.json()
            if "audio_url" not in result:
                logger.bind(tag=TAG).error("响应中缺少音频地址")
                return

            # 下载音频文件
            audio_resp = requests.get(result["audio_url"])
            audio_resp.raise_for_status()
            
            # 保存文件
            with open(output_file, "wb") as f:
                f.write(audio_resp.content)
                
            logger.bind(tag=TAG).info(f"音频文件已保存至: {output_file}")

        except requests.exceptions.HTTPError as e:
            logger.bind(tag=TAG).error(f"HTTP请求失败: {str(e)}")
        except requests.exceptions.JSONDecodeError:
            logger.bind(tag=TAG).error("响应解析失败，无效的JSON格式")
        except Exception as e:
            logger.bind(tag=TAG).error(f"语音合成失败: {str(e)}")