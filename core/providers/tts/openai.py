import os
import uuid
# import logging
from datetime import datetime
from openai import OpenAI
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url")
        self.model_name = config.get("model_name", "tts-1")
                
        if not self.api_key:
            raise ValueError("OpenAI API key is required but not provided in config")
        
        self.voice = config.get("voice", "alloy")
        
        try:
            # Initialize OpenAI client with custom base URL if provided
            if self.api_url:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_url
                )
            else:
                self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize OpenAI client: {str(e)}")
            raise

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        if not text or not output_file:
            raise ValueError("Both text and output_file must be provided")

        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            logger.bind(tag=TAG).info(f"Generating speech for text: {text}")
            logger.bind(tag=TAG).info(f"Using API URL: {self.api_url if self.api_url else 'default OpenAI URL'}")
            
            response = self.client.audio.speech.create(
                model=self.model_name,
                voice=self.voice,
                input=text
            )
            
            # Save the audio file
            response.stream_to_file(output_file)
            
            # Verify file was created
            if not os.path.exists(output_file):
                raise Exception("Failed to create audio file")
            else:
                logger.bind(tag=TAG).info(f"Successfully created audio file: {output_file}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"OpenAI TTS generation failed: {str(e)}")
            raise Exception(f"OpenAI TTS generation failed: {str(e)}")
