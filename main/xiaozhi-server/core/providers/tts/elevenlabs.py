import os
import uuid
import requests
from datetime import datetime
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    try:
        # Fallback import pattern
        from elevenlabs import ElevenLabs
        ELEVENLABS_AVAILABLE = True
    except ImportError:
        ELEVENLABS_AVAILABLE = False

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        if not ELEVENLABS_AVAILABLE:
            raise ImportError("ElevenLabs package not installed. Please run: pip install elevenlabs==2.41.0")
        
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.elevenlabs.io/v1/text-to-speech")
        self.voice_id = config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Default Rachel voice
        self.model_id = config.get("model_id", "eleven_turbo_v2_5")
        self.stability = config.get("stability", 0.5)
        self.similarity_boost = config.get("similarity_boost", 0.5)
        self.style = config.get("style", 0.0)
        self.use_speaker_boost = config.get("use_speaker_boost", True)
        self.optimize_streaming_latency = config.get("optimize_streaming_latency", 0)
        self.output_format = config.get("output_format", "mp3_44100_128")
        self.audio_file_type = "mp3"  # ElevenLabs typically returns MP3
        self.output_file = config.get("output_dir", "tmp/")

        # Initialize ElevenLabs client
        try:
            self.client = ElevenLabs(api_key=self.api_key)
            logger.bind(tag=TAG).debug("ElevenLabs client initialized successfully")
            
            # Debug: Log available methods on the client
            available_methods = [method for method in dir(self.client) if not method.startswith('_')]
            logger.bind(tag=TAG).debug(f"Available ElevenLabs client methods: {available_methods}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize ElevenLabs client: {e}")
            raise ImportError("Could not initialize ElevenLabs client. Please check SDK version and API key.")

        logger.debug(
            f"ElevenLabs TTS parameters initialized: voice_id={self.voice_id}, "
            f"model_id={self.model_id}, output_format={self.output_format}, "
            f"stability={self.stability}, similarity_boost={self.similarity_boost}"
        )
        
        model_key_msg = check_model_key("ElevenLabs TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            
        # Validate API key format
        if not self.api_key or self.api_key == "your_elevenlabs_api_key":
            logger.bind(tag=TAG).error("ElevenLabs API key is not configured. Please set a valid API key in config.yaml")
            
        # Log configuration for debugging
        logger.bind(tag=TAG).info(f"ElevenLabs TTS initialized with voice: {self.voice_id}, model: {self.model_id}")

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    def _voice_settings(self):
        """Voice settings honored by every call path (SDK + raw requests)."""
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
        }

    async def text_to_speak(self, text, output_file):
        logger.bind(tag=TAG).debug(f"Sending ElevenLabs TTS request with voice_id: {self.voice_id}, text length: {len(text)}")
        
        try:
            # Use ElevenLabs SDK streaming API for better performance
            logger.bind(tag=TAG).debug(f"Generating audio with ElevenLabs SDK streaming")
            
            # Use the streaming method for real-time audio generation
            audio_stream = self.client.text_to_speech.stream(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format=self.output_format,
                voice_settings=self._voice_settings()
            )
            
            # Collect all audio chunks from the stream
            audio_chunks = []
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            
            audio_data = b"".join(audio_chunks)
            logger.bind(tag=TAG).debug(f"ElevenLabs TTS streaming successful, audio size: {len(audio_data)} bytes")
            
            if output_file:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                
                logger.bind(tag=TAG).debug(f"ElevenLabs TTS audio saved to: {output_file}")
            else:
                return audio_data
                
        except Exception as e:
            # Fallback to non-streaming method if streaming fails
            logger.bind(tag=TAG).warning(f"ElevenLabs streaming failed, trying convert method: {str(e)}")
            try:
                # Try the convert method as fallback
                audio_data = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    output_format=self.output_format,
                    voice_settings=self._voice_settings()
                )
                
                # Handle both bytes and generator responses
                if hasattr(audio_data, '__iter__') and not isinstance(audio_data, (bytes, str)):
                    # It's a generator, collect the chunks
                    audio_chunks = []
                    for chunk in audio_data:
                        if isinstance(chunk, bytes):
                            audio_chunks.append(chunk)
                    audio_data = b"".join(audio_chunks)
                
                logger.bind(tag=TAG).debug(f"ElevenLabs TTS convert successful, audio size: {len(audio_data)} bytes")
                
                if output_file:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    with open(output_file, "wb") as f:
                        f.write(audio_data)
                    
                    logger.bind(tag=TAG).debug(f"ElevenLabs TTS audio saved to: {output_file}")
                else:
                    return audio_data
                    
            except Exception as e2:
                # Final fallback to requests-based implementation
                logger.bind(tag=TAG).warning(f"ElevenLabs SDK completely failed, falling back to requests: {str(e2)}")
                try:
                    await self._fallback_text_to_speak(text, output_file)
                except Exception as e3:
                    logger.bind(tag=TAG).error(f"All ElevenLabs methods failed: SDK={str(e)}, Convert={str(e2)}, Requests={str(e3)}")
                    raise Exception(f"ElevenLabs TTS completely failed. Please check API key and network connection.")
    
    async def _fallback_text_to_speak(self, text, output_file):
        """Fallback implementation using requests"""
        url = f"{self.api_url}/{self.voice_id}"
        
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
        
        # Add optional parameters if specified
        if self.optimize_streaming_latency > 0:
            data["optimize_streaming_latency"] = self.optimize_streaming_latency
        
        if self.output_format != "mp3_44100_128":
            data["output_format"] = self.output_format
        
        logger.bind(tag=TAG).debug(f"Making ElevenLabs TTS API request to: {url}")
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.bind(tag=TAG).debug(f"ElevenLabs TTS request successful, audio size: {len(response.content)} bytes")
                
                if output_file:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    with open(output_file, "wb") as f:
                        f.write(response.content)
                    
                    logger.bind(tag=TAG).debug(f"ElevenLabs TTS audio saved to: {output_file}")
                else:
                    return response.content
            else:
                # Parse error response for better error messages
                error_detail = "Unknown error"
                try:
                    error_json = response.json()
                    if 'detail' in error_json:
                        if isinstance(error_json['detail'], dict) and 'message' in error_json['detail']:
                            error_detail = error_json['detail']['message']
                        else:
                            error_detail = str(error_json['detail'])
                    else:
                        error_detail = response.text
                except:
                    error_detail = response.text
                
                if response.status_code == 401:
                    error_msg = f"ElevenLabs API authentication failed: {error_detail}. Please check your API key and permissions."
                elif response.status_code == 429:
                    error_msg = f"ElevenLabs API rate limit exceeded: {error_detail}. Please wait and try again."
                elif response.status_code == 400:
                    error_msg = f"ElevenLabs API bad request: {error_detail}. Please check your configuration."
                else:
                    error_msg = f"ElevenLabs TTS request failed ({response.status_code}): {error_detail}"
                
                logger.bind(tag=TAG).error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"ElevenLabs TTS request error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"ElevenLabs TTS unexpected error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
