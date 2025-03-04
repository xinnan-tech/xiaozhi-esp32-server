import json
from config.logger import setup_logging
import requests
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url", "https://api.dify.ai/v1").rstrip('/')

    def response(self, session_id, dialogue):
        try:
            # 取最后一条用户消息
            last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

            # 发起流式请求
            with requests.post(
                    f"{self.base_url}/chat-messages",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": last_msg["content"],
                        "response_mode": "streaming",
                        "user": session_id,
                        "inputs": {}
                    },
                    stream=True
            ) as r:
                for line in r.iter_lines():
                    if line.startswith(b'data: '):
                        event = json.loads(line[6:])
                        if event.get('answer'):
                            yield event['answer']

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")
            yield "【服务响应异常】"
