import json
import requests
from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.flow_id = config["flow_id"]
        self.base_url = config.get("base_url", "https://api.langflow.astra.datastax.com").rstrip("/")
        self.tweaks = config.get("tweaks", {})
        model_key_msg = check_model_key("LangflowLLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def response(self, session_id, dialogue, **kwargs):
        last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

        request_json = {
            "input_value": last_msg["content"],
            "output_type": "chat",
            "input_type": "chat",
        }

        if session_id:
            request_json["session_id"] = session_id

        if self.tweaks:
            request_json["tweaks"] = self.tweaks

        try:
            url = f"{self.base_url}/api/v1/run/{self.flow_id}?stream=true"
            with requests.post(
                url,
                headers={"x-api-key": self.api_key},
                json=request_json,
                stream=True,
            ) as r:
                for line in r.iter_lines():
                    if not line or line.startswith(b":"):
                        continue
                    if line.startswith(b"data: "):
                        line = line[6:]
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("event") == "token":
                            token_data = data.get("data", {})
                            if isinstance(token_data, dict):
                                chunk = token_data.get("chunk", "")
                                if chunk:
                                    yield chunk
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.bind(tag=TAG).error(f"Langflow API error: {e}")
