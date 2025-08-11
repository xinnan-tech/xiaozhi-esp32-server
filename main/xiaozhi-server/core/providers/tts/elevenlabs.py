import requests
import json
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    """
    ElevenLabs TTS Provider
    Supports high-quality voice synthesis with multiple voices and languages
    """
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key","sk_7bbbc42db83364614c2e07da3991c16a91256df9e7281f37")
        if not self.api_key:    
            raise ValueError("ElevenLabs API key is required")
        self.voice_id = config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Default to Rachel voice
        self.model_id = config.get("model_id", "eleven_multilingual_v2")  # Default multilingual model
        
        # ElevenLabs API endpoint
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        
        # Voice settings
        self.stability = float(config.get("stability", "0.75"))
        self.similarity_boost = float(config.get("similarity_boost", "0.75"))
        self.style = float(config.get("style", "0.0"))  # For v2 models
        self.use_speaker_boost = config.get("use_speaker_boost", True)
        
        # Output format (ElevenLabs supports mp3, pcm, ulaw, mulaw)
        self.output_format = config.get("output_format", "mp3_44100_128")
        self.audio_file_type = "mp3" if "mp3" in self.output_format else "wav"
        
        # Streaming settings
        self.optimize_streaming_latency = int(config.get("optimize_streaming_latency", "0"))
        
        self.output_file = config.get("output_dir", "tmp/")
        
        model_key_msg = check_model_key("ElevenLabs TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        
        # Validate API key format
        if self.api_key and len(self.api_key) < 32:
            logger.bind(tag=TAG).warning("ElevenLabs API key appears to be too short. Please check your API key.")

    async def text_to_speak(self, text, output_file):
        """
        Convert text to speech using ElevenLabs API
        """
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost
            }
        }
        
        # Add streaming optimization if specified
        if self.optimize_streaming_latency > 0:
            params = {
                "optimize_streaming_latency": self.optimize_streaming_latency,
                "output_format": self.output_format
            }
        else:
            params = {
                "output_format": self.output_format
            }
        
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                if output_file:
                    with open(output_file, "wb") as audio_file:
                        audio_file.write(response.content)
                    logger.bind(tag=TAG).debug(f"ElevenLabs TTS saved to: {output_file}")
                else:
                    return response.content
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                raise Exception(
                    f"ElevenLabs TTS request failed: {response.status_code} - {error_data}"
                )
                
        except requests.exceptions.Timeout:
            raise Exception("ElevenLabs TTS request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"ElevenLabs TTS network error: {str(e)}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"ElevenLabs TTS error: {str(e)}")
            raise

    def get_available_voices(self):
        """
        Helper method to get available voices from ElevenLabs
        """
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        try:
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            )
            
            if response.status_code == 200:
                voices = response.json()["voices"]
                return [(v["voice_id"], v["name"]) for v in voices]
            else:
                logger.bind(tag=TAG).error(f"Failed to fetch voices: {response.status_code}")
                return []
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error fetching voices: {str(e)}")
            return []