from config.logger import setup_logging
from http import HTTPStatus
import dashscope
from dashscope import Application
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key
import time

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.app_id = config["app_id"]
        self.base_url = config.get("base_url")
        self.is_No_prompt = config.get("is_no_prompt")
        self.memory_id = config.get("ali_memory_id")
        self.streaming_chunk_size = config.get("streaming_chunk_size", 3)  # 每次流式返回的字符数
        check_model_key("AliBLLLM", self.api_key)

    def response(self, session_id, dialogue):
        # 处理dialogue
        if self.is_No_prompt:
            dialogue.pop(0)
            logger.bind(tag=TAG).debug(
                f"【阿里百练API服务】处理后的dialogue: {dialogue}"
            )

        # 构造调用参数
        call_params = {
            "api_key": self.api_key,
            "app_id": self.app_id,
            "session_id": session_id,
            "messages": dialogue,
            # 开启SDK原生流式
            "stream": True,
        }
        if self.memory_id != False:
            # 百练memory需要prompt参数
            prompt = dialogue[-1].get("content")
            call_params["memory_id"] = self.memory_id
            call_params["prompt"] = prompt
            logger.bind(tag=TAG).debug(
                f"【阿里百练API服务】处理后的prompt: {prompt}"
            )

        # 可选地设置自定义API基地址（若配置为兼容模式URL则忽略）
        if self.base_url and ("/api/" in self.base_url):
            dashscope.base_http_api_url = self.base_url

        responses = Application.call(**call_params)

        # 流式处理（SDK在stream=True时返回可迭代对象；否则返回单次响应对象）
        logger.bind(tag=TAG).debug(
            f"【阿里百练API服务】构造参数: {dict(call_params, api_key='***')}"
        )

        last_text = ""
        try:
            for resp in responses:
                if resp.status_code != HTTPStatus.OK:
                    logger.bind(tag=TAG).error(
                        f"code={resp.status_code}, message={resp.message}, 请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code"
                    )
                    continue
                current_text = getattr(getattr(resp, "output", None), "text", None)
                if current_text is None:
                    continue
                # SDK流式为增量覆盖，计算差量输出
                if len(current_text) >= len(last_text):
                    delta = current_text[len(last_text):]
                else:
                    # 避免偶发回退
                    delta = current_text
                if delta:
                    yield delta
                last_text = current_text
        except TypeError:
            # 非流式回落（一次性返回）
            if responses.status_code != HTTPStatus.OK:
                logger.bind(tag=TAG).error(
                    f"code={responses.status_code}, message={responses.message}, 请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code"
                )
                yield "【阿里百练API服务响应异常】"
            else:
                full_text = getattr(getattr(responses, "output", None), "text", "")
                logger.bind(tag=TAG).info(
                    f"【阿里百练API服务】完整响应长度: {len(full_text)}"
                )
                for i in range(0, len(full_text), self.streaming_chunk_size):
                    chunk = full_text[i:i + self.streaming_chunk_size]
                    if chunk:
                        yield chunk

    def response_with_functions(self, session_id, dialogue, functions=None):
        # 阿里百练当前未支持原生的 function call。为保持兼容，这里回退到普通文本流式输出。
        # 上层会按 (content, tool_calls) 的形式消费，这里始终返回 (token, None)
        logger.bind(tag=TAG).warning(
            "阿里百练未实现原生 function call，已回退为纯文本流式输出"
        )
        for token in self.response(session_id, dialogue):
            yield token, None
