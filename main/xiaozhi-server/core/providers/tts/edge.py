import os

import uuid

import edge_tts

from datetime import datetime

from core.providers.tts.base import TTSProviderBase

class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):

        super().__init__(config, delete_audio_file)

        if config.get("private_voice"):

            self.voice = config.get("private_voice")

        else:

            self.voice = config.get("voice")

        self.audio_file_type = config.get("format", "mp3")

    def generate_filename(self, extension=".mp3"):

        return os.path.join(

            self.output_file,

            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",

        )

    async def text_to_speak(self, text, output_file):

        try:

            communicate = edge_tts.Communicate(text, voice=self.voice)

            if output_file:

                # Ensure directory exists and create empty file

                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                with open(output_file, "wb") as f:

                    pass

                # Stream write audio data

                with open(output_file, "ab") as f: # Change to append mode to avoid overwrite

                    async for chunk in communicate.stream():

                        if chunk["type"] == "audio": # Only process audio data chunks

                            f.write(chunk["data"])

            else:

                # Return audio binary data

                audio_bytes = b""

                async for chunk in communicate.stream():

                    if chunk["type"] == "audio":

                        audio_bytes += chunk["data"]

                return audio_bytes

        except Exception as e:

            error_msg = f"Edge TTS request failed: {e}"

            raise Exception(error_msg) # Throw exception for caller to catch