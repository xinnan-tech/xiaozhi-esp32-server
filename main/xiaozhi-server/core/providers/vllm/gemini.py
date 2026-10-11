from google import generativeai as genai
from google.generativeai import types

from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.vllm.base import VLLMProviderBase

TAG = __name__
logger = setup_logging()


class VLLMProvider(VLLMProviderBase):
    """Gemini vision provider for image analysis (config: VLLM.GeminiVLLM)."""

    def __init__(self, config):
        self.model_name = config.get("model_name", "gemini-1.5-pro")
        self.api_key = config.get("api_key")

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

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        logger.debug(
            f"Gemini VLLM parameters initialized: model_name={self.model_name}, "
            f"max_tokens={self.max_tokens}, temperature={self.temperature}, top_p={self.top_p}"
        )

    def response(self, question, base64_image):
        logger.bind(
            tag=TAG
        ).debug(
            f"Sending Gemini vision request with model: {self.model_name}, "
            f"question length: {len(question)}, image size: {len(base64_image) if base64_image else 0}"
        )
        question = question + "(Please reply in English)"
        try:
            content = [
                question,
                {
                    "mime_type": "image/jpeg",
                    "data": base64_image,
                },
            ]
            generation_config = types.GenerationConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )
            resp = self.model.generate_content(
                content, generation_config=generation_config
            )
            result = resp.text
            if not result:
                logger.bind(tag=TAG).warning("Gemini vision request returned no text")
                return "Sorry, I couldn't analyze the image."
            return result
        except Exception as e:
            logger.bind(tag=TAG).error(f"Gemini vision request error: {e}")
            return "Oops! Something went wrong, please try again later."
