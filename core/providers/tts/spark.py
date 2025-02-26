# coding: utf-8
import ssl
import uuid
import websocket
import json
import base64
import os
import time
import threading
import hashlib
import hmac
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase, logger, TAG
from core.utils.util import read_config, get_project_dir

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.appid = config.get("appid")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.is_finished = False  # 用于标记是否已完成音频接收

        if not self.api_key or not self.api_secret:
            raise ValueError("Xunfei API key and secret are required but not provided in config")
    
        self.voice = config.get("voice", "xiaoyan")
        self.sample_rate = config.get("sample_rate", 16000)
        self.ws_url = "wss://tts-api.xfyun.cn/v2/tts"
        self.common_args = {"app_id": self.appid}
        self.business_args = {
            "aue": "lame",
            "auf": "audio/L16;rate=16000",
            "vcn": self.voice,
            "tte": "utf8"
        }
        self.text = None
        self.my_output_file = None
            
            
    def create_url(self):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        
        url = self.ws_url + '?' + urlencode(v)
        return url
    
    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        # """
        # 语音合成接口
        # :param text: 需要合成的文本
        # :param output_file: 输出音频文件的路径
        # :return: 返回合成音频的文件路径
        # """
        if not text or not output_file:
            raise ValueError("Both text and output_file must be provided")   
        
        try:     
            self.text = text
            self.my_output_file = output_file
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            self.run()

            # Verify file was created
            if not os.path.exists(output_file):
                raise Exception("Failed to create audio file")
            else:
                logger.bind(tag=TAG).debug(f"Successfully created audio file: {output_file}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"SparkTTS generation failed: {str(e)}")
            raise Exception(f"SparkTTS generation failed: {str(e)}")

    def on_message(self, ws, message):
        try:
            message = json.loads(message)
            code = message["code"]
            sid = message["sid"]
            audio = message["data"]["audio"]
            audio = base64.b64decode(audio)
            status = message["data"]["status"]
            logger.bind(tag=TAG).debug(f"message: {message}")

            if status == 2:  # 最后一帧
                logger.bind(tag=TAG).debug(f"Received the last frame, closing websocket.")
                self.is_finished = True
                ws.close()

            if code != 0:
                errMsg = message["message"]
                logger.bind(tag=TAG).error(f"sid:{sid} call error: {errMsg} code is:{code}")
            else:
                file_to_save = open(self.my_output_file, "wb")
                file_to_save.write(audio)
                # file_to_save.write(base64.b64decode(data))                
                # with open(self.output_file, 'ab') as f:
                    # f.write(audio)

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error while receiving message: {e}")

    def on_error(self, ws, error):
        logger.bind(tag=TAG).error(f"Error: {error}")
        self.is_finished = True

    def on_close(self, ws, close_status_code, close_msg):
        logger.bind(tag=TAG).debug(f"WebSocket closed.")
        self.is_finished = True

    def on_open(self, ws):
        def run(*args):
            data = {
                "common": self.common_args,
                "business": self.business_args,
                "data": {"status": 2, "text": str(base64.b64encode(self.text.encode('utf-8')), "UTF8")}
            }
            data = json.dumps(data)
            logger.bind(tag=TAG).debug(f"Sending text data to server...")
            ws.send(data)

        threading.Thread(target=run).start()

    def run(self):
        ws_url = self.create_url()
        ws = websocket.WebSocketApp(ws_url,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.on_open = self.on_open
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # 等待音频接收完成后再退出
        while not self.is_finished:
            time.sleep(0.1)  # 等待直到接收到最后一帧或发生错误

        logger.bind(tag=TAG).debug(f"WebSocket session finished.")        


# 例子
if __name__ == "__main__":
    config = {
        "appid": "xxxx",
        "api_key": "xxxx",
        "api_secret": "xxxx",
        "voice": "xiaoyan",
        "sample_rate": 16000
    }

    provider = TTSProvider(config, False)
    output_file = provider.generate_filename(extension=".mp3")
    provider.text_to_speak("这是一个语音合成示例", output_file)
    logger.bind(tag=TAG).debug(f"合成的语音文件保存到: {output_file}")
