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
        
        # 初始化语音设置
        default_voice_setting = {
            "voice_id": "female-shaonv",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy",
        }
        default_pronunciation_dict = {"tone": ["处理/(chu3)(li3)", "危险/dangerous"]}
        default_audio_setting = {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        }
        
        # 合并配置
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
        self.timber_weights = parse_string_to_list(config.get("timber_weights"))
        
        # 设置语音ID
        if config.get("private_voice"):
            self.voice_setting["voice_id"] = config.get("private_voice")
        elif config.get("voice_id"):
            self.voice_setting["voice_id"] = config.get("voice_id")
        
        # WebSocket配置
        self.ws_url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "GroupId": self.group_id
        }
        self.audio_file_type = self.audio_setting.get("format", "mp3")

    def generate_filename(self, extension=".mp3"):
        """生成唯一的音频文件名"""
        return os.path.join(
            self.output_file,
            f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def _establish_connection(self):
        """建立WebSocket连接"""
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
                print("连接成功")
                return ws
            return None
        except Exception as e:
            print(f"连接失败: {e}")
            return None

    async def _start_task(self, websocket):
        """发送任务开始请求"""
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
        """发送继续请求并收集音频数据"""
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
        """关闭连接"""
        if websocket:
            await websocket.send(json.dumps({"event": "task_finish"}))
            await websocket.close()
            print("连接已关闭")

    async def text_to_speak(self, text, output_file=None):
        """主方法：文本转语音"""
        ws = await self._establish_connection()
        if not ws:
            raise Exception("无法建立WebSocket连接")

        try:
            if not await self._start_task(ws):
                raise Exception("任务启动失败")

            hex_audio = await self._continue_task(ws, text)
            audio_bytes = bytes.fromhex(hex_audio)

            # 保存到文件或返回二进制数据
            if output_file:
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
                print(f"音频已保存为{output_file}")
                return output_file
            else:
                # 返回音频二进制数据（不播放）
                return audio_bytes

        finally:
            await self._close_connection(ws)


async def main():
    """测试用主函数"""
    # 示例配置
    config = {
        "group_id": "YOUR_GROUP_ID",  # 替换为实际的group_id
        "api_key": "YOUR_API_KEY",    # 替换为实际的api_key
        "model": "your-model",        # 替换为实际的模型名称
        "voice_id": "male-qn-qingse",
        "voice_setting": {
            "speed": 1.2,
            "emotion": "happy"
        }
    }
    
    tts = TTSProvider(config, delete_audio_file=True)
    output_file = tts.generate_filename()
    await tts.text_to_speak("这是一个测试文本，用于验证流式语音合成功能", output_file)


if __name__ == "__main__":
    asyncio.run(main())