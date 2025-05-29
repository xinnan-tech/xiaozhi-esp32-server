import requests
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase
from core.utils.util import parse_string_to_list

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.refer_wav_path = config.get("refer_wav_path")
        self.prompt_text = config.get("prompt_text")
        self.prompt_language = config.get("prompt_language")
        self.text_language = config.get("text_language", "audo")

        # 处理空字符串的情况
        top_k = config.get("top_k", "15")
        top_p = config.get("top_p", "1.0")
        temperature = config.get("temperature", "1.0")
        sample_steps = config.get("sample_steps", "32")
        speed = config.get("speed", "1.0")

        self.top_k = int(top_k) if top_k else 15
        self.top_p = float(top_p) if top_p else 1.0
        self.temperature = float(temperature) if temperature else 1.0
        self.sample_steps = int(sample_steps) if sample_steps else 32
        self.speed = float(speed) if speed else 1.0

        self.cut_punc = config.get("cut_punc", "")
        self.inp_refs = parse_string_to_list(config.get("inp_refs"))
        self.if_sr = str(config.get("if_sr", False)).lower() in ("true", "1", "yes")

    async def text_to_speak(self, text, output_file):
        request_params = {
            "refer_wav_path": self.refer_wav_path,
            "prompt_text": self.prompt_text,
            "prompt_language": self.prompt_language,
            "text": text,
            "text_language": self.text_language,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "cut_punc": self.cut_punc,
            "speed": self.speed,
            "inp_refs": self.inp_refs,
            "sample_steps": self.sample_steps,
            "if_sr": self.if_sr,
        }

        resp = requests.get(self.url, params=request_params)
        if resp.status_code == 200:
            with open(output_file, "wb") as file:
                file.write(resp.content)
        else:
            error_msg = f"GPT_SoVITS_V3 TTS请求失败: {resp.status_code} - {resp.text}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
