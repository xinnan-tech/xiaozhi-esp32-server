import json
from config.logger import setup_logging
import requests
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url")
        self.detail = config.get("detail", False)
        self.variables = config.get("variables", {})
        check_model_key("FastGPTLLM", self.api_key)

    def response(self, session_id, dialogue):
        try:
            # 取最后一条用户消息
            last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

            # 发起流式请求
            with requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "stream": True,
                    "chatId": session_id,
                    "detail": self.detail,
                    "variables": self.variables,
                    "messages": [{"role": "user", "content": last_msg["content"]}],
                },
                stream=True,
            ) as r:
                for line in r.iter_lines():
                    if line:
                        try:
                            if line.startswith(b"data: "):
                                if line[6:].decode("utf-8") == "[DONE]":
                                    break

                                data = json.loads(line[6:])
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if (
                                        delta
                                        and "content" in delta
                                        and delta["content"] is not None
                                    ):
                                        content = delta["content"]
                                        if "<think>" in content:
                                            continue
                                        if "</think>" in content:
                                            continue
                                        yield content

                        except json.JSONDecodeError as e:
                            continue
                        except Exception as e:
                            continue

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")
            yield "【服务响应异常】"

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).info(f"fastgpt暂未实现完整的工具调用（function call）")
        return self.response(session_id, dialogue)
