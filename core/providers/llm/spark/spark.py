# coding: utf-8
import json
import base64
import hmac
import hashlib
import ssl
import websocket
from urllib.parse import urlencode, urlparse
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from core.providers.llm.base import LLMProviderBase
from config.logger import setup_logging
import queue

TAG = __name__
logger = setup_logging()

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.appid = config.get("appid")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.base_url = config.get("base_url")
        self.model_name = config.get("model_name", "4.0Ultra")
        if "你" in self.api_key:
            logger.bind(tag=TAG).error("你还没配置LLM的密钥，请在配置文件中配置密钥，否则无法正常工作")

        self.host = urlparse(self.base_url).netloc
        self.path = urlparse(self.base_url).path
        self.query_url = self.create_url()
        self.response_queue = queue.Queue()  # 用来收集WebSocket的响应

    def create_url(self):
        # 生成访问讯飞星火API的URL
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'), hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')

        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        params = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        return self.base_url + '?' + urlencode(params)

    def on_message(self, ws, message):
        # 处理接收到的消息
        data = json.loads(message)
        code = data['header']['code']
        if code != 0:
            logger.bind(tag=TAG).error(f'请求错误: {code}, {data}')
            ws.close()
        else:
            choices = data["payload"]["choices"]
            status = choices["status"]
            content = choices["text"][0]["content"]
            if content:
                self.response_queue.put(content)  # 收集内容
            if status == 2:
                logger.bind(tag=TAG).info("会话结束")
                ws.close()

    def on_error(self, ws, error):
        # 处理WebSocket错误
        logger.bind(tag=TAG).error(f"WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        # 处理WebSocket关闭
        logger.bind(tag=TAG).info(f"WebSocket已关闭，状态码: {close_status_code}, 消息: {close_msg}")

    def on_open(self, ws):
        # 处理WebSocket连接打开
        # 发送请求数据
        request_data = self.gen_params(ws.query)
        logger.bind(tag=TAG).debug(f"request_data: {request_data}")
        ws.send(json.dumps(request_data))

    def gen_params(self, query):
        # 生成WebSocket请求参数
        data = {
            "header": {
                "app_id": self.appid,
                "uid": "1234",  # 可根据需要生成或传入实际UID
            },
            "parameter": {
                "chat": {
                    "domain": self.model_name,
                    "temperature": 0.5,
                    "max_tokens": 4096,
                }
            },
            "payload": {
                "message": {
                    "text": query
                }
            }
        }
        return data

    def run_websocket(self, query):
        # 启动WebSocket连接并发送请求
        ws = websocket.WebSocketApp(self.query_url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close, on_open=self.on_open)
        ws.appid = self.appid
        ws.query = query
        logger.bind(tag=TAG).debug(f"ws.query: {ws.query}")
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def response(self, session_id, dialogue):
        # 生成LLM的响应（通过WebSocket获取流式响应）
        try:
            # 启动WebSocket连接并获取流式数据
            logger.bind(tag=TAG).debug(f"dialogue: {dialogue}")
            if dialogue == "":
                logger.bind(tag=TAG).error("对话内容为空")
                dialogue = "你好"
                
            self.run_websocket(dialogue)
            # 通过Queue来获取响应内容
            while not self.response_queue.empty():
                yield self.response_queue.get()  # 返回队列中的内容
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取LLM响应时发生错误: {e}")

# windows下执行 $env:PYTHONPATH="../../../../"; python spark.py 进行测试
# Linux/MacOS下执行 PYTHONPATH=../../../../ python your_script.py 进行测试
if __name__ == "__main__":
    config = {
        "appid": "xxxx",
        "api_key": "xxxx",
        "api_secret": "xxxx",
        "base_url": "wss://spark-api.xf-yun.com/v4.0/chat",
        "model_name": "4.0Ultra",
    }

    provider = LLMProvider(config)
    session_id = "1234"
    dialogue = "给我写一篇100字的作文"
    data = [{"role": "user", "content": dialogue}]
    
    for content in provider.response(session_id, data):
        logger.bind(tag=TAG).info(f"content: {content}")
