from pathlib import Path
from core.utils.util import parse_string_to_list
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging
from fishaudio import FishAudio, TTSConfig

TAG = __name__
logger = setup_logging()



def audio_to_bytes(file_path):
    if not file_path or not Path(file_path).exists():
        return None
    with open(file_path, "rb") as wav_file:
        wav = wav_file.read()
    return wav


def read_ref_text(ref_text):
    path = Path(ref_text)
    if path.exists() and path.is_file():
        with path.open("r", encoding="utf-8") as file:
            return file.read()
    return ref_text


class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.model = config.get("model", "s1")
        if config.get("reference_id"):
            self.reference_id = config.get("reference_id")
        else:
            self.reference_id = None
        self.reference_audio = parse_string_to_list(
             config.get('ref_audio')if config.get('ref_audio') else config.get("reference_audio")
        )
        self.reference_text = parse_string_to_list(
             config.get('ref_text')if config.get('ref_text') else config.get("reference_text")
        )
        self.format = config.get("response_format", "pcm")
        self.sample_rate = config.get("sample_rate", 16000)
        self.audio_file_type = config.get("response_format", "pcm")
        self.api_key = config.get("api_key", "YOUR_API_KEY")
        if self.api_key is None:
            raise ValueError("FishSpeech API key is required")
        self._client = FishAudio(api_key=self.api_key)
        
        self.normalize = str(config.get("normalize", True)).lower() in (
            "true",
            "1",
            "yes",
        )

        # 处理空字符串的情况
        channels = config.get("channels", "1")
        rate = config.get("rate", "44100")
        max_new_tokens = config.get("max_new_tokens", "1024")
        chunk_length = config.get("chunk_length", "200")

        self.channels = int(channels) if channels else 1
        self.rate = int(rate) if rate else 44100
        self.max_new_tokens = int(max_new_tokens) if max_new_tokens else 1024
        self.chunk_length = int(chunk_length) if chunk_length else 200

        # 处理空字符串的情况
        top_p = config.get("top_p", "0.7")
        temperature = config.get("temperature", "0.7")
        repetition_penalty = config.get("repetition_penalty", "1.2")

        self.top_p = float(top_p) if top_p else 0.7
        self.temperature = float(temperature) if temperature else 0.7
        self.repetition_penalty = (
            float(repetition_penalty) if repetition_penalty else 1.2
        )

        self.streaming = str(config.get("streaming", False)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.use_memory_cache = config.get("use_memory_cache", "on")
        self.seed = int(config.get("seed")) if config.get("seed") else None

    async def text_to_speak(self, text, output_file):
        logger.bind(tag=TAG).info(f"fish speech synthesize text: {text}")

        audio_stream = self._client.tts.stream(
            text=text,
            reference_id=self.reference_id,
            model=self.model,
            config=TTSConfig(
                format=self.format,
                sample_rate=self.sample_rate,
                normalize=self.normalize,
                latency="balanced",
            ),
        )

        audio_bytes = b''
    
        for chunk in audio_stream:
            if chunk:
                audio_bytes += chunk
       
        if output_file:
            with open(output_file, "wb") as audio_file:
                audio_file.write(audio_bytes)
        else:
            return audio_bytes
