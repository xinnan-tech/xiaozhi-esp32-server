import os
import uuid
import json
import asyncio
import websockets
import ssl
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from core.utils.util import parse_string_to_list


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.group_id = config.get("group_id")
        self.api_key = config.get("api_key")
        self.model = config.get("model")

        # Initialize voice settings
        default_voice_setting = {
            "voice_id": "female-shaonv",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy",
        }
        default_pronunciation_dict = {
            "tone": ["处理/(chu3)(li3)", "危险/dangerous"]}
        default_audio_setting = {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        }

        # Merge configurations
        self.voice_setting = {
            **default_voice_setting,
            **config.get("voice_setting", {}),
        }

        self.pronunciation_dict = {
            **default_pronunciation_dict,
            **config.get("pronunciation_dict", {}),
        }

        self.audio_setting = {
            **default_audio_setting,
            **config.get("audio_setting", {})
        }

        self.timber_weights = parse_string_to_list(
            config.get("timber_weights"))

        # Set voice ID
        if config.get("private_voice"):
            self.voice_setting["voice_id"] = config.get("private_voice")
        elif config.get("voice_id"):
            self.voice_setting["voice_id"] = config.get("voice_id")

        # WebSocket configuration
        self.ws_url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "GroupId": self.group_id
        }

        self.audio_file_type = self.audio_setting.get("format", "mp3")

    def generate_filename(self, extension=".mp3"):
        """Generate unique audio filename"""
        return os.path.join(
            self.output_file,
            f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def _establish_connection(self):
        """Establish WebSocket connection"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            ws = await websockets.connect(
                self.ws_url,
                additional_headers=self.headers,
                ssl=ssl_context
            )

            connected = json.loads(await ws.recv())
            if connected.get("event") == "connected_success":
                print("Connection successful")
                return ws
            return None

        except Exception as e:
            print(f"Connection failed: {e}")
            return None

    async def _start_task(self, websocket):
        """Send task start request"""
        start_msg = {
            "event": "task_start",
            "model": self.model,
            "voice_setting": self.voice_setting,
            "pronunciation_dict": self.pronunciation_dict,
            "audio_setting": self.audio_setting
        }

        if self.timber_weights and len(self.timber_weights) > 0:
            start_msg["timber_weights"] = self.timber_weights
            start_msg["voice_setting"]["voice_id"] = ""

        await websocket.send(json.dumps(start_msg))
        response = json.loads(await websocket.recv())
        return response.get("event") == "task_started"

    async def _continue_task(self, websocket, text):
        """Send continue request and collect audio data"""
        await websocket.send(json.dumps({
            "event": "task_continue",
            "text": text
        }))

        audio_chunks = []
        while True:
            response = json.loads(await websocket.recv())
            if "data" in response and "audio" in response["data"]:
                audio_chunks.append(response["data"]["audio"])
            if response.get("is_final"):
                break

        return "".join(audio_chunks)

    async def _close_connection(self, websocket):
        """Close connection"""
        if websocket:
            await websocket.send(json.dumps({"event": "task_finish"}))
            await websocket.close()
            print("Connection closed")

    async def text_to_speak(self, text, output_file=None):
        """Main method: text to speech"""
        ws = await self._establish_connection()
        if not ws:
            raise Exception("Unable to establish WebSocket connection")

        try:
            if not await self._start_task(ws):
                raise Exception("Task start failed")

            hex_audio = await self._continue_task(ws, text)
            audio_bytes = bytes.fromhex(hex_audio)

            # Save to file or return binary data
            if output_file:
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
                print(f"Audio saved as {output_file}")
                return output_file
            else:
                # Return audio binary data (no playback)
                return audio_bytes

        finally:
            await self._close_connection(ws)


async def main():
    """Test main function"""
    # Example configuration
    config = {
        "group_id": "YOUR_GROUP_ID",  # Replace with actual group_id
        "api_key": "YOUR_API_KEY",   # Replace with actual api_key
        "model": "your-model",       # Replace with actual model name
        "voice_id": "male-qn-qingse",
        "voice_setting": {
            "speed": 1.2,
            "emotion": "happy"
        }
    }

    tts = TTSProvider(config, delete_audio_file=True)
    output_file = tts.generate_filename()
    await tts.text_to_speak("This is a test text to verify streaming speech synthesis functionality", output_file)

if __name__ == "__main__":
    asyncio.run(main())
