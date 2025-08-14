import requests
import json
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    """
    SiliconFlow CosyVoice TTS Provider
    Supports high-quality voice synthesis with CosyVoice models
    """
    
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # API configuration
        self.access_token = config.get("access_token")
        if not self.access_token:
            raise ValueError("SiliconFlow access token is required")
        
        # Model configuration - default to CosyVoice2-0.5B
        self.model = config.get("model", "FunAudioLLM/CosyVoice2-0.5B")
        
        # Voice configuration - default to diana with model prefix
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            voice_name = config.get("voice", "diana")
            # If voice doesn't already contain model prefix, add it
            if ":" not in voice_name:
                self.voice = f"{self.model}:{voice_name}"
            else:
                self.voice = voice_name
        
        # Audio format configuration
        self.response_format = config.get("response_format", "mp3")
        self.audio_file_type = self.response_format
        
        # Audio parameters
        self.speed = float(config.get("speed", 1.0))
        self.gain = config.get("gain", 0)
        
        # API endpoint
        self.api_url = "https://api.siliconflow.com/v1/audio/speech"
        
        # Validate API key
        model_key_msg = check_model_key("SiliconFlow TTS", self.access_token)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        
        if self.access_token and len(self.access_token) < 32:
            logger.bind(tag=TAG).warning(
                "SiliconFlow access token appears to be too short. Please check your token.")
        
        logger.bind(tag=TAG).info(f"SiliconFlow TTS initialized with model: {self.model}, voice: {self.voice}")
    
    async def text_to_speak(self, text, output_file):
        """
        Convert text to speech using SiliconFlow CosyVoice API
        """
        # Prepare request payload - based on your original API example
        payload = {
            "input": text,
            "response_format": self.response_format,
            "stream": True,  # Enable streaming as in your example
            "speed": self.speed,
            "gain": self.gain,
            "model": self.model
        }
        
        # Add voice parameter with model prefix (e.g., FunAudioLLM/CosyVoice2-0.5B:diana)
        if self.voice:
            payload["voice"] = self.voice
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.bind(tag=TAG).debug(f"SiliconFlow TTS request: {text[:50]}...")
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                if output_file:
                    with open(output_file, "wb") as audio_file:
                        audio_file.write(response.content)
                    logger.bind(tag=TAG).debug(f"SiliconFlow TTS saved to: {output_file}")
                else:
                    return response.content
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                except:
                    error_data = response.text
                
                raise Exception(
                    f"SiliconFlow TTS request failed: {response.status_code} - {error_data}"
                )
                
        except requests.exceptions.Timeout:
            raise Exception("SiliconFlow TTS request timed out")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"SiliconFlow TTS network error: {str(e)}")
        
        except Exception as e:
            logger.bind(tag=TAG).error(f"SiliconFlow TTS error: {str(e)}")
            raise
    
    def get_available_voices(self):
        """
        Helper method to get available voices for CosyVoice
        Returns voices with model prefix format
        """
        model_prefix = self.model
        return [
            (f"{model_prefix}:diana", "Diana (Female)"),
            (f"{model_prefix}:alex", "Alex (Male)"),
            (f"{model_prefix}:bella", "Bella (Female)"),
        ]
