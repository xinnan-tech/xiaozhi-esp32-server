import openai
import json
import re
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.vllm.base import VLLMProviderBase

TAG = __name__
logger = setup_logging()

VISION_RESPONSE_INSTRUCTION = (
    "\n请只用中文一到两句话回答，最多80个汉字；"
    "不要使用标题、列表、Markdown，也不要补充与画面无关的信息。"
)


def limit_vision_response(text, max_chars=80):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    normalized = re.sub(r"[*#`]", "", normalized)
    sentences = [part for part in re.split(r"(?<=[。！？!?])", normalized) if part]
    limited = "".join(sentences[:2]).strip() if sentences else normalized
    if len(limited) > max_chars:
        limited = limited[: max_chars - 1].rstrip("，,；;、 ") + "。"
    return limited


class VLLMProvider(VLLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")

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

        model_key_msg = check_model_key("VLLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, question, base64_image):
        question = question + VISION_RESPONSE_INSTRUCTION
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=False,
                temperature=self.temperature,
                top_p=self.top_p,
            )

            return limit_vision_response(response.choices[0].message.content)

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")
            raise
