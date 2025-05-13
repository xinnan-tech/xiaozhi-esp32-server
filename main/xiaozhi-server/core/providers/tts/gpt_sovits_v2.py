import os
import uuid
import json
import base64
import requests
from config.logger import setup_logging
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from core.utils.util import parse_string_to_list

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.text_lang = config.get("text_lang", "zh")
        self.ref_audio_path = config.get("ref_audio_path")
        self.prompt_text = config.get("prompt_text")
        self.prompt_lang = config.get("prompt_lang", "zh")

        # 处理空字符串的情况
        top_k = config.get("top_k", "5")
        top_p = config.get("top_p", "1")
        temperature = config.get("temperature", "1")
        batch_threshold = config.get("batch_threshold", "0.75")
        batch_size = config.get("batch_size", "1")
        speed_factor = config.get("speed_factor", "1.0")
        seed = config.get("seed", "-1")
        repetition_penalty = config.get("repetition_penalty", "1.35")

        self.top_k = int(top_k) if top_k else 5
        self.top_p = float(top_p) if top_p else 1
        self.temperature = float(temperature) if temperature else 1
        self.batch_threshold = float(batch_threshold) if batch_threshold else 0.75
        self.batch_size = int(batch_size) if batch_size else 1
        self.speed_factor = float(speed_factor) if speed_factor else 1.0
        self.seed = int(seed) if seed else -1
        self.repetition_penalty = (
            float(repetition_penalty) if repetition_penalty else 1.35
        )

        self.text_split_method = config.get("text_split_method", "cut0")

        self.split_bucket = str(config.get("split_bucket", True)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.return_fragment = str(config.get("return_fragment", False)).lower() in (
            "true",
            "1",
            "yes",
        )

        self.streaming_mode = str(config.get("streaming_mode", False)).lower() in (
            "true",
            "1",
            "yes",
        )

        self.parallel_infer = str(config.get("parallel_infer", True)).lower() in (
            "true",
            "1",
            "yes",
        )

        self.aux_ref_audio_paths = parse_string_to_list(
            config.get("aux_ref_audio_paths")
        )

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        request_json = {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": self.ref_audio_path,
            "aux_ref_audio_paths": self.aux_ref_audio_paths,
            "prompt_text": self.prompt_text,
            "prompt_lang": self.prompt_lang,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "text_split_method": self.text_split_method,
            "batch_size": self.batch_size,
            "batch_threshold": self.batch_threshold,
            "split_bucket": self.split_bucket,
            "return_fragment": self.return_fragment,
            "speed_factor": self.speed_factor,
            "streaming_mode": self.streaming_mode,
            "seed": self.seed,
            "parallel_infer": self.parallel_infer,
            "repetition_penalty": self.repetition_penalty,
        }

        resp = requests.post(self.url, json=request_json)
        if resp.status_code == 200:
            with open(output_file, "wb") as file:
                file.write(resp.content)
        else:
            error_msg = f"GPT_SoVITS_V2 TTS请求失败: {resp.status_code} - {resp.text}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
