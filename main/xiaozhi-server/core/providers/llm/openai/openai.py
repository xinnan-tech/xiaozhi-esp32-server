import httpx
import openai
from openai.types import CompletionUsage
from openai.types.responses import Response
from openai.types.responses import (
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseTextDeltaEvent, 
    ResponseFunctionCallArgumentsDeltaEvent, 
    ResponseFunctionCallArgumentsDoneEvent
)
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase
from types import SimpleNamespace
import time


TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        # 增加timeout的配置项，单位为秒
        timeout = config.get("timeout", 300)
        self.timeout = int(timeout) if timeout else 300

        param_defaults = {
            "max_tokens": (500, int),
            "temperature": (0.7, lambda x: round(float(x), 1)),
            "top_p": (1.0, lambda x: round(float(x), 1)),
            "frequency_penalty": (0, lambda x: round(float(x), 1)),
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

        logger.debug(
            f"意图识别参数初始化: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=httpx.Timeout(self.timeout))

    def response(self, session_id, dialogue, **kwargs):
        try:
            responses = self.client.responses.create(
                model=self.model_name,
                input=dialogue,
                stream=True,
                max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
            )

            for chunk in responses:
                if isinstance(chunk, ResponseTextDeltaEvent):
                    yield chunk.delta

        except Exception as e:
            try:
                error_msg = repr(e)
            except:
                error_msg = "encoding error"
            logger.bind(tag=TAG).error(f"Error in response generation: {error_msg}")

    def response_with_functions(self, session_id, dialogue, functions=None):
        tools = None
        if functions:
            tools = []
            for f in functions:
                if f.get("type") == "function" and "function" in f:
                    func = f["function"]
                    tools.append({
                        "type": "function",
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),

                    })
                else:
                    # 已经是 Responses API 格式，移除不支持的字段
                    tool = {k: v for k, v in f.items() if k != "strict"}
                    tools.append(tool)

        try:
            # 构建请求参数
            request_params = {
                "model": self.model_name,
                "input": dialogue,
                "stream": True,
                "max_output_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }
            
            # 只有在有 tools 时才添加 tools 参数
            if tools:
                request_params["tools"] = tools
            
            stream = self.client.responses.create(**request_params)

            for chunk in stream:
                if isinstance(chunk, ResponseOutputItemAddedEvent):
                    if chunk.item.type == "function_call":
                        yield None, [SimpleNamespace(
                            id=chunk.item.call_id,
                            type="function",
                            function=SimpleNamespace(
                                name=chunk.item.name,
                            ),
                        )]
                elif isinstance(chunk, ResponseFunctionCallArgumentsDeltaEvent):
                    yield None, [SimpleNamespace(
                            function=SimpleNamespace(
                                arguments=chunk.item.arguments,
                            ),
                        )]
                elif isinstance(chunk, ResponseTextDeltaEvent):
                    yield chunk.delta, None

        except Exception as e:
            try:
                error_msg = repr(e)
            except:
                error_msg = "encoding error"
            logger.bind(tag=TAG).error(f"Error in function call streaming: {error_msg}")
            yield "OpenAI service error", None
