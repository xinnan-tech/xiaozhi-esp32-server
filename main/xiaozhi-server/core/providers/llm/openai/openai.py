import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase

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

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )

    # =============== 修正版 response() =================
    def response(self, session_id, dialogue, **kwargs):
        try:
            # ✅ 清理 messages 中缺失 content 的项，防止 400 错误
            clean_dialogue = []
            fixed_count = 0
            for msg in dialogue:
                if "role" not in msg:
                    continue
                if "content" not in msg or msg["content"] is None:
                    msg["content"] = ""
                    fixed_count += 1
                clean_dialogue.append(msg)
            if fixed_count > 0:
                logger.bind(tag=TAG).warning(
                    f"修正了 {fixed_count} 条对话消息（缺失 content 已补空字符串）"
                )

            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=clean_dialogue,
                stream=True,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                frequency_penalty=kwargs.get(
                    "frequency_penalty", self.frequency_penalty
                ),
            )

            is_active = True
            for chunk in responses:
                try:
                    delta = (
                        chunk.choices[0].delta
                        if getattr(chunk, "choices", None)
                        else None
                    )
                    content = delta.content if hasattr(delta, "content") else ""
                except IndexError:
                    content = ""
                if content:
                    if "<think>" in content:
                        is_active = False
                        content = content.split("<think>")[0]
                    if "</think>" in content:
                        is_active = True
                        content = content.split("</think>")[-1]
                    if is_active:
                        yield content

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")

    # =============== 修正版 response_with_functions() =================
    def response_with_functions(self, session_id, dialogue, functions=None):
        try:
            # ✅ 清理消息列表
            clean_dialogue = []
            fixed_count = 0
            for msg in dialogue:
                if "role" not in msg:
                    continue
                if "content" not in msg or msg["content"] is None:
                    msg["content"] = ""
                    fixed_count += 1
                clean_dialogue.append(msg)
            if fixed_count > 0:
                logger.bind(tag=TAG).warning(
                    # f"修正了 {fixed_count} 条函数调用消息（缺失 content 已补空字符串）"
                )

            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=clean_dialogue,
                stream=True,
                tools=functions,
            )

            for chunk in stream:
                if getattr(chunk, "choices", None):
                    yield chunk.choices[0].delta.content, chunk.choices[
                        0
                    ].delta.tool_calls
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    usage_info = getattr(chunk, "usage", None)
                    logger.bind(tag=TAG).info(
                        f"Token 消耗：输入 {getattr(usage_info, 'prompt_tokens', '未知')}，"
                        f"输出 {getattr(usage_info, 'completion_tokens', '未知')}，"
                        f"共计 {getattr(usage_info, 'total_tokens', '未知')}"
                    )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in function call streaming: {e}")
            yield f"【OpenAI服务响应异常: {e}】", None
