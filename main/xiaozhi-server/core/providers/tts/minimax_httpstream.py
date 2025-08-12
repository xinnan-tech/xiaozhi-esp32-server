import os
import uuid
import json
import requests
from datetime import datetime
from typing import Iterator, Optional, Union
from core.providers.tts.base import TTSProviderBase
from core.utils.util import parse_string_to_list


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.group_id = config.get("group_id")
        self.api_key = config.get("api_key")
        self.model = config.get("model")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice_id")

        default_voice_setting = {
            "voice_id": "female-shaonv",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy",
        }
        default_pronunciation_dict = {"tone": ["处理/(chu3)(li3)", "危险/dangerous"]}
        defult_audio_setting = {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        }
        self.voice_setting = {
            **default_voice_setting,
            **config.get("voice_setting", {}),
        }
        self.pronunciation_dict = {
            **default_pronunciation_dict,
            **config.get("pronunciation_dict", {}),
        }
        self.audio_setting = {**defult_audio_setting, **config.get("audio_setting", {})}
        self.timber_weights = parse_string_to_list(config.get("timber_weights"))

        if self.voice:
            self.voice_setting["voice_id"] = self.voice

        self.host = "api.minimax.chat"
        self.api_url = f"https://{self.host}/v1/t2a_v2?GroupId={self.group_id}"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.audio_file_type = defult_audio_setting.get("format", "mp3")

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        """非流式语音合成（保留原有实现）"""
        request_json = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": self.voice_setting,
            "pronunciation_dict": self.pronunciation_dict,
            "audio_setting": self.audio_setting,
        }

        if type(self.timber_weights) is list and len(self.timber_weights) > 0:
            request_json["timber_weights"] = self.timber_weights
            request_json["voice_setting"]["voice_id"] = ""

        try:
            resp = requests.post(
                self.api_url, json.dumps(request_json), headers=self.header
            )
            if resp.json()["base_resp"]["status_code"] == 0:
                data = resp.json()["data"]["audio"]
                audio_bytes = bytes.fromhex(data)
                if output_file:
                    with open(output_file, "wb") as file_to_save:
                        file_to_save.write(audio_bytes)
                else:
                    return audio_bytes
            else:
                raise Exception(
                    f"{__name__} status_code: {resp.status_code} response: {resp.content}"
                )
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")

    def text_to_speak_stream(
        self, 
        text: str, 
        chunk_callback: Optional[callable] = None
    ) -> Iterator[bytes]:
        """
        流式语音合成方法
        :param text: 要合成的文本
        :param chunk_callback: 可选的回调函数，用于处理每个音频块
        :return: 生成器，每次产生一个音频数据块(bytes)
        """
        request_json = {
            "model": self.model,
            "text": text,
            "stream": True,
            "voice_setting": self.voice_setting,
            "pronunciation_dict": self.pronunciation_dict,
            "audio_setting": self.audio_setting,
        }

        if isinstance(self.timber_weights, list) and len(self.timber_weights) > 0:
            request_json["timber_weights"] = self.timber_weights
            request_json["voice_setting"]["voice_id"] = ""

        try:
            with requests.post(
                self.api_url,
                data=json.dumps(request_json),
                headers=self.header,
                stream=True
            ) as response:
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    raise Exception(
                        f"HTTP error: {response.status_code}, response: {response.text}"
                    )
                
                # 处理流式响应
                for line in response.iter_lines():
                    if line:  # 过滤空行
                        # 检查是否为数据行 (SSE格式)
                        if line.startswith(b'data:'):
                            try:
                                data = json.loads(line[5:].strip())  # 去掉"data:"前缀
                                
                                # 检查API状态码
                                if data.get("base_resp", {}).get("status_code", -1) != 0:
                                    raise Exception(
                                        f"API error: {data.get('base_resp', {}).get('status_msg')}"
                                    )
                                
                                # 跳过非音频数据块
                                if "extra_info" in data:
                                    continue
                                    
                                # 提取音频数据
                                audio_hex = data.get("data", {}).get("audio")
                                if audio_hex:
                                    audio_chunk = bytes.fromhex(audio_hex)
                                    if chunk_callback:
                                        chunk_callback(audio_chunk)
                                    yield audio_chunk
                                    
                            except json.JSONDecodeError:
                                # 忽略JSON解析错误（可能是心跳包等）
                                continue
                            except Exception as e:
                                raise e
                                
        except Exception as e:
            raise Exception(f"{__name__} stream error: {e}")

    def save_stream_to_file(
        self, 
        text: str, 
        output_file: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        流式合成并保存到文件
        :param text: 要合成的文本
        :param output_file: 输出文件路径，如果为None则自动生成
        :param progress_callback: 可选的回调函数，接收已写入的字节数
        :return: 保存的文件路径
        """
        if not output_file:
            output_file = self.generate_filename(extension=f".{self.audio_file_type}")
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        total_bytes = 0
        try:
            with open(output_file, "wb") as audio_file:
                for audio_chunk in self.text_to_speak_stream(text):
                    audio_file.write(audio_chunk)
                    audio_file.flush()
                    total_bytes += len(audio_chunk)
                    if progress_callback:
                        progress_callback(total_bytes)
            return output_file
        except Exception as e:
            # 清理可能创建的不完整文件
            if os.path.exists(output_file):
                os.remove(output_file)
            raise e

    def stream_to_audio_player(self, text: str, player_command: list = None):
        """
        流式合成并直接播放音频
        :param text: 要合成的文本
        :param player_command: 音频播放器命令，默认使用mpv
        """
        if player_command is None:
            player_command = ["mpv", "--no-cache", "--no-terminal", "--", "fd://0"]
        
        try:
            import subprocess
            player_process = subprocess.Popen(
                player_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            for audio_chunk in self.text_to_speak_stream(text):
                player_process.stdin.write(audio_chunk)
                player_process.stdin.flush()
                
            player_process.stdin.close()
            player_process.wait()
        except Exception as e:
            raise Exception(f"Audio player error: {e}")