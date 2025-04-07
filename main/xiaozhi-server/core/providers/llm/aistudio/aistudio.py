from config.logger import setup_logging
import requests
import json
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.app_id = config.get("app_id")
        self.secret_key = config.get("secret_key")
        self.base_url = config.get("base_url")

        if not self.app_id or not self.secret_key:
            # logger.bind(tag=TAG).error("Missing app_id or secret_key in config")
            raise ValueError("app_id and secret_key are required for Wenxin LLM")

    def _construct_payload(self, session_id, dialogue):
        last_message = dialogue[-1]["content"] if dialogue else ""
        return {
            "message": {
                "content": {
                    "type": "text",
                    "value": {"showText": last_message}
                }
            },
            "source": self.app_id,
            "from": "openapi",
            "openId": session_id
        }

    def response(self, session_id, dialogue):
        try:
            url = f"{self.base_url}?appId={self.app_id}&secretKey={self.secret_key}"
            headers = {"Content-Type": "application/json"}
            payload = self._construct_payload(session_id, dialogue)

            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            response.raise_for_status()

            buffer = ""
            for chunk in response.iter_content(chunk_size=1024):
                buffer += chunk.decode('utf-8')
                while '\n\n' in buffer:
                    event_part, _, buffer = buffer.partition('\n\n')
                    for line in event_part.split('\n'):
                        if line.startswith('data:'):
                            data = json.loads(line[len('data:'):].strip())
                            if data.get("status") != 0 or data.get("data") is None:
                                # logger.bind(tag=TAG).error(f"API error: {data.get('message')}")
                                continue

                            message = data["data"].get("message", {})
                            contents = message.get("content", [])
                            for content in contents:
                                if not content["isFinished"] and content.get("data"):
                                    text = content["data"].get("text", "")
                                    if text.strip():
                                        yield text

        except requests.exceptions.RequestException as e:
            logger.bind(tag=TAG).error(f"Request failed: {str(e)}")
            yield "【网络请求异常，请稍后重试】"
        except json.JSONDecodeError as e:
            logger.bind(tag=TAG).error(f"JSON decode error: {str(e)}")
            yield "【服务响应解析错误】"
        except Exception as e:
            logger.bind(tag=TAG).error(f"Unexpected error: {str(e)}")
            yield "【文心服务响应异常】"

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).warning("Function calling not supported by Wenxin LLM")
        for chunk in self.response(session_id, dialogue):
            yield {"type": "content", "content": chunk}