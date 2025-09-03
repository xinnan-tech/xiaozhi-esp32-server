import requests
import base64
import wave
import io
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.api_url = config.get(
            "api_url", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent")
        self.model = config.get("model", "gemini-2.5-flash-preview-tts")
        self.voice_name = config.get("voice", "Zephyr")
        self.language = config.get("language", "en")
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/")

        model_key_msg = check_model_key("TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    async def text_to_speak(self, text, output_file):
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": text
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.voice_name
                        }
                    }
                }
            }
        }

        try:
            logger.bind(tag=TAG).debug(f"Gemini TTS request: {data}")
            response = requests.post(self.api_url, json=data, headers=headers)
            logger.bind(tag=TAG).debug(f"Gemini TTS response status: {response.status_code}")

            if response.status_code == 200:
                response_json = response.json()
                
                # Extract audio data from the response
                if "candidates" in response_json and len(response_json["candidates"]) > 0:
                    candidate = response_json["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "inlineData" in part and "data" in part["inlineData"]:
                                # Decode base64 audio data
                                audio_data = base64.b64decode(part["inlineData"]["data"])
                                
                                # Convert PCM to WAV format
                                wav_data = self._pcm_to_wav(audio_data)
                                
                                if output_file:
                                    with open(output_file, "wb") as audio_file:
                                        audio_file.write(wav_data)
                                else:
                                    return wav_data
                                return
                
                raise Exception("No audio data found in response")
            else:
                raise Exception(
                    f"Gemini TTS request failed: {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Gemini TTS failed: {e}")
            raise

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM data to WAV format"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM data is empty, cannot convert to WAV")
            return b""

        # Create WAV file header for Gemini's 24kHz, 16-bit, mono PCM
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)      # Mono
                wav_file.setsampwidth(2)      # 16-bit
                wav_file.setframerate(24000)  # 24kHz sample rate (Gemini default)
                wav_file.writeframes(pcm_data)

            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV conversion failed: {e}")
            return b""