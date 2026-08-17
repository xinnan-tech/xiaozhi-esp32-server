from core.providers.vllm.base import VLLMProviderBase


class VLLMProvider(VLLMProviderBase):
    """Route vision requests to the currently selected multimodal LLM.

    This provider intentionally has no endpoint settings.  The image and its
    question are appended to the current conversation, so the normal ``LLM``
    configuration supplies the model, credentials, and response handling.
    """

    def __init__(self, config):
        self.config = config

    def use_multimodal_llm(self) -> bool:
        return True

    def response(self, question, base64_image):
        raise RuntimeError("multimodal_llm 供应器应由主 LLM 处理图片请求")
