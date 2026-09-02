import io
import wave
import json
import base64
import asyncio
import websockets
import numpy as np
from datetime import datetime
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase



TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url", "ws://192.168.1.10:8092/paddlespeech/tts/streaming")
        self.protocol = config.get("protocol", "websocket")
        
        if config.get("private_voice"):
            self.spk_id = int(config.get("private_voice"))
        else:
            self.spk_id = int(config.get("spk_id", "0"))
            
        sample_rate = config.get("sample_rate", 24000)
        self.sample_rate = float(sample_rate) if sample_rate else 24000
        
        speed = config.get("speed", 1.0)
        self.speed = float(speed) if speed else 1.0
        
        volume = config.get("volume", 1.0)
        self.volume = float(volume) if volume else 1.0
        
        self.delete_audio_file = config.get("delete_audio", True)
        if not self.delete_audio_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = config.get("save_path")
            if save_path:
                if not save_path.endswith('.wav'):
                    save_path = f"{save_path}_{timestamp}.wav"
                else:
                    other_path = save_path[:-4]
                    save_path = f"{other_path}_{timestamp}.wav"
                self.save_path = save_path
            else:
                self.save_path = f"./streaming_tts_{timestamp}.wav"
        else:
            self.save_path = None

    async def pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 24000, num_channels: int = 1,
                         bits_per_sample: int = 16) -> bytes:
    async def pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 24000, num_channels: int = 1,
                         bits_per_sample: int = 16) -> bytes:
        """
        Convert PCM data to WAV file and return byte data
        :param pcm_data: PCM data (raw byte stream)
        :param sample_rate: Audio sampling rate, default is 24000
        :param num_channels: Number of channels, default is mono
        :param bits_per_sample: Bits per sample, default is 16
        :return: WAV format byte data
        """
        byte_data = np.frombuffer(pcm_data, dtype=np.int16)  # 16-bit PCM
        wav_io = io.BytesIO()

        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(byte_data.tobytes())

        return wav_io.getvalue()

    async def text_to_speak(self, text, output_file):
        if self.protocol == "websocket":
            return await self.text_streaming(text, output_file)
        else:
            raise ValueError("Unsupported protocol. Please use 'websocket' or 'http'.")

    async def text_streaming(self, text, output_file):
        try:
            # Connect to WebSocket server asynchronously using websockets
            async with websockets.connect(self.url) as ws:
                # Send start request
                start_request = {
                    "task": "tts",
                    "signal": "start"
                }
                await ws.send(json.dumps(start_request))

                # Receive start response and extract session_id
                start_response = await ws.recv()
                start_response = json.loads(start_response)  # Parse JSON response
                if start_response.get("status") != 0:
                    raise Exception(f"Connection failed: {start_response.get('signal')}")

                session_id = start_response.get("session")

                # Send text data to be synthesized
                data_request = {
                    "text": text,
                    "spk_id": self.spk_id,
                }
                await ws.send(json.dumps(data_request))

                audio_chunks = b""
                timeout_seconds = 60  # Set timeout
                try:
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
                        response = json.loads(response)  # Parse JSON response
                        status = response.get("status")

                        if status == 2:  # Last packet
                            break
                        else:
                            # Concatenate audio data (base64 encoded PCM data)
                            audio_chunks += base64.b64decode(response.get("audio"))
                except asyncio.TimeoutError:
                    raise Exception(f"WebSocket timeout: waiting for audio data exceeded {timeout_seconds} seconds")

                # Convert concatenated PCM data to WAV format
                wav_data = await self.pcm_to_wav(audio_chunks)

                # End request
                end_request = {
                    "task": "tts",
                    "signal": "end",
                    "session": session_id  # Session ID must match start request
                }
                await ws.send(json.dumps(end_request))

                # Receive end response to avoid exception
                await ws.recv()

                # Decide whether to save file based on config
                if not self.delete_audio_file and self.save_path:
                    with open(self.save_path, "wb") as f:
                        f.write(wav_data)
                    logger.bind(tag=TAG).info(f"Audio file saved to: {self.save_path}")
                
                # Return or save audio data
                if output_file:
                    with open(output_file, "wb") as file_to_save:
                        file_to_save.write(wav_data)
                else:
                    return wav_data

        except Exception as e:
            raise Exception(f"Error during TTS WebSocket request: {e} while processing text: {text}")