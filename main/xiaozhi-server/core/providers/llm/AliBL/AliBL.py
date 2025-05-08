from config.logger import setup_logging
from http import HTTPStatus
from dashscope import Application
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.app_id = config["app_id"]
        self.base_url = config.get("base_url")
        self.is_No_prompt = config.get("is_no_prompt")
        self.memory_id = config.get("ali_memory_id")
        check_model_key("AliBLLLM", self.api_key)

    def response(self, session_id, dialogue):
        try:
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
            }
            if self.memory_id != False:
                # 百练memory需要prompt参数
                prompt = dialogue[-1].get("content")
                call_params["memory_id"] = self.memory_id
                call_params["prompt"] = prompt
                logger.bind(tag=TAG).debug(
                    f"【阿里百练API服务】处理后的prompt: {prompt}"
                )

            responses = Application.call(**call_params)
            if responses.status_code != HTTPStatus.OK:
                logger.bind(tag=TAG).error(
                    f"code={responses.status_code}, "
                    f"message={responses.message}, "
                    f"请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code"
                )
                yield "【阿里百练API服务响应异常】"
            else:
                logger.bind(tag=TAG).debug(
                    f"【阿里百练API服务】构造参数: {call_params}"
                )
                yield responses.output.text

        except Exception as e:
            logger.bind(tag=TAG).error(f"【阿里百练API服务】响应异常: {e}")
            yield "【LLM服务响应异常】"

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).info(f"阿里百练暂未实现完整的工具调用（function call）")
        return self.response(session_id, dialogue)
