import openai
import json
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.vllm.base import VLLMProviderBase

TAG = __name__
logger = setup_logging()


class VLLMProvider(VLLMProviderBase):
    def __init__(self, config):
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"

        self.base_url = f"https://{self.host}/v1"
        self.model_name = config.get("model_name")
    

        param_defaults = {
            "max_tokens": (500, int),
            "temperature": (0.7, lambda x: round(float(x), 1)),
            "top_p": (1.0, lambda x: round(float(x), 1)),
        }

        for param, (default, converter) in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self,
                    param,
                    converter(value) if value not in (None, "") else default,
                )
            except (ValueError, TypeError):
                setattr(self, param, default)

        check_model_key("VLLM", self.api_key)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, question, base64_image):
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"{base64_image}"},
                        },
                    ],
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model_name, messages=messages, stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")
            raise
