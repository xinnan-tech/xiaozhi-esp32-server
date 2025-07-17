"""
This module provides an implementation of a VLLM (Vision Language and Large Model) provider
for the Volcengine service. It allows interaction with multimodal models that can process
both text and images.
"""
import json

import openai

from config.logger import setup_logging
from core.providers.vllm.base import VLLMProviderBase
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class VLLMProvider(VLLMProviderBase):
    """
    Implements the VLLM provider for Volcengine, supporting multimodal interactions.

    This class handles the configuration, client initialization, and communication
    with the Volcengine API to get responses from vision-language models.
    """

    def __init__(self, config):
        """
        Initializes the VLLMProvider for Volcengine.

        Args:
            config (dict): A dictionary containing the configuration for the VLLM provider,
                         including API key, model name, host, and other parameters.
        """
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"

        self.base_url = f"https://{self.host}/v1"
        self.model_name = config.get("model_name")
    

        # Default parameters for the model, with type converters.
        param_defaults = {
            "max_tokens": (500, int),
            "temperature": (0.7, lambda x: round(float(x), 1)),
            "top_p": (1.0, lambda x: round(float(x), 1)),
        }

        # Set model parameters from config, falling back to defaults.
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
        """
        Sends a request to the Volcengine VLLM service with a question and an image.

        Args:
            question (str): The text question to ask the model.
            base64_image (str): The base64-encoded image data to be sent with the question.

        Returns:
            str: The text response from the model.

        Raises:
            Exception: If there is an error during the API call.
        """
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
