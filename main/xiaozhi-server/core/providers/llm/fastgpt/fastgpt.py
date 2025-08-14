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
        model_key_msg = check_model_key("FastGPTLLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)


    def response(self, session_id, dialogue, **kwargs):
        try:
            # Get the last user message
            last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")


            # Initiate streaming request
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
            yield "[Service Response Exception]"


    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).error(
            f"FastGPT has not yet implemented complete tool calling (function call), it is recommended to use other intent recognition methods"
        )