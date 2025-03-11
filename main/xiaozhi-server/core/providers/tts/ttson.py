import os
import uuid
import json
import hashlib
import random
import requests
import shutil
from urllib.parse import quote
from datetime import datetime
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url", "https://u95167-bd74-2aef8085.westx.seetacloud.com:8443/flashsummary/tts?token=")
        self.voice_id = config.get("voice_id", 1695)
        self.token = config.get("token")
        self.to_lang = config.get("to_lang")
        self.volume_change_dB = config.get("volume_change_dB", 0)
        self.speed_factor = config.get("speed_factor", 1)
        self.stream = config.get("stream", False)
        self.output_file = config.get("output_file")
        self.pitch_factor = config.get("pitch_factor", 0)
        self.format = config.get("format", "mp3")
        self.emotion = config.get("emotion", 1)
        self.appid = config.get("appid")
        self.key = config.get("key")
        self.baidu_url = config.get("baidu_url")
        self.header = {
            "Content-Type": "application/json"
        }

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        url = f'{self.url}{self.token}'
        result = "firefly"
        if self.to_lang == "ZH":
            payload = json.dumps({
               "to_lang": self.to_lang,
               "text": text,
               "emotion": self.emotion,
               "format": self.format,
               "volume_change_dB": self.volume_change_dB,
               "voice_id": self.voice_id,
               "pitch_factor": self.pitch_factor,
               "speed_factor": self.speed_factor,
               "token": self.token
        })
        else:
            # 配置参数（替换成你的实际值）
            appid = self.appid        # 你的应用ID
            secret_key = self.key   # 你的密钥
            q = text             # 要翻译的中文文本
            from_lang = "zh"            # 源语言：中文
            to_lang = "jp"              # 目标语言：日语（百度API中日语代码为`jp`）

            # 生成随机数 salt
            salt = random.randint(10000, 99999)

            # Step 1: 拼接签名字符串（使用变量名）
            sign_str = f"{appid}{q}{salt}{secret_key}"

            # Step 2: 计算 MD5 签名
            sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

            # Step 3: 对中文文本进行 URL 编码
            encoded_q = quote(q)

            # Step 4: 构建请求 URL
            url_1 = f"https://fanyi-api.baidu.com/api/trans/vip/translate?" \
                f"q={encoded_q}&from={from_lang}&to={to_lang}&" \
              f"appid={appid}&salt={salt}&sign={sign}"

            # Step 5: 发送 GET 请求
            response = requests.get(url_1)
            result = response.json()
            if response.status_code != 200:
                print("error:",response.status_code)
            else:
                # 获取翻译结果（兼容字段缺失、空列表等异常情况）
                try:
                   trans_list = result.get("trans_result", [])
                   if trans_list:
                       dst = trans_list[0].get("dst", "翻译结果不存在")
                   else:
                       dst = "无翻译结果"
                except (IndexError, AttributeError) as e:
                    dst = f"解析错误: {str(e)}"
                print(dst)
                print(response.status_code)
                payload = json.dumps({
                    "to_lang": self.to_lang,
                    "text": dst,
                    "emotion": self.emotion,
                    "format": self.format,
                    "volume_change_dB": self.volume_change_dB,
                    "voice_id": self.voice_id,
                    "pitch_factor": self.pitch_factor,
                    "speed_factor": self.speed_factor,
                    "token": self.token
                })
               
        resp = requests.request("POST", url, data=payload)
        if resp.status_code != 200:
            return None
        resp_json = resp.json()
        try:
            result = resp_json['url'] + ':' + str(
                resp_json[
                    'port']) + '/flashsummary/retrieveFileData?stream=True&token=' + self.token + '&voice_audio_path=' + \
                     resp_json['voice_path']
        except Exception as e:
            print("error:", e)

        audio_content = requests.get(result)
        with open(output_file, "wb") as f:
            f.write(audio_content.content)
            return True
        voice_path = resp_json.get("voice_path")
        des_path = output_file
        shutil.move(voice_path, des_path)
