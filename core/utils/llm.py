import json
import logging
import openai
import requests
from datetime import datetime
from core.utils.util import is_segment
from core.utils.util import get_string_no_punctuation_or_emoji
from core.utils.util import read_config, get_project_dir
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLM(ABC):
    @abstractmethod
    def response(self, session_id, dialogue):
        """LLM response generator"""
        pass


class DeepSeekLLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        self.base_url = config.get("url")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, session_id, dialogue):
        logger.info(f"Generating response using {dialogue}")
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            for chunk in responses:
                # 检查是否存在有效的choice且content不为空
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', '')
                    if content:  # 仅在content非空时生成
                        yield content
        except Exception as e:
            logger.error(f"Error in response generation: {e}")


class ChatGLMLLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        self.base_url = config.get("url")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, session_id, dialogue):
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            for chunk in responses:
                # 检查是否存在有效的choice且content不为空
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', '')
                    if content:  # 仅在content非空时生成
                        yield content
        except Exception as e:
            logger.error(f"Error in response generation: {e}")

class AliLLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, session_id, dialogue):
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            for chunk in responses:
                # 检查是否存在有效的choice且content不为空
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', '')
                    if content:  # 仅在content非空时生成
                        yield content
        except Exception as e:
            logger.error(f"Error in response generation: {e}")

class DifyLLM(LLM):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url", "https://api.dify.ai/v1").rstrip('/')
    
    def response(self, session_id, dialogue):
        try:
            # 取最后一条用户消息
            last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")
            #
            logger.info(f"Base URL: {self.base_url}")
            logger.info(f"API Key: {self.api_key}")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Last Message: {last_msg}")

            # 发起流式请求
            response_content = []
            with requests.post(
                    f"{self.base_url}/chat-messages",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": last_msg["content"],
                        "response_mode": "streaming",
                        "user": session_id,
                        "inputs": {}
                    },
                    stream=True
            ) as r:
                for line in r.iter_lines():
                    if line.startswith(b'data: '):
                        event = json.loads(line[6:])
                        if event.get('answer'):
                            yield event['answer']
                            response_content.append(event['answer'])
            logger.info(f"Response Content: {response_content}")

        except Exception:
            yield "【服务响应异常】"


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls_map = {
        "DeepSeekLLM": DeepSeekLLM,
        "ChatGLMLLM": ChatGLMLLM,
        "DifyLLM": DifyLLM,
        "AliLLM": AliLLM,
        # 可扩展其他LLM实现
    }

    if cls := cls_map.get(class_name):
        return cls(*args, **kwargs)
    raise ValueError(f"不支持的LLM类型: {class_name}")


if __name__ == "__main__":
    """
      响应速度测试
    """
    config = read_config(get_project_dir() + "config.yaml")
    llm = create_instance(
        config["selected_module"]["LLM"],
        config["LLM"][config["selected_module"]["LLM"]]
    )

    start_time = datetime.now()

    dialogue = []
    dialogue.append({"role": "system", "content": config.get("prompt")})
    dialogue.append({"role": "user", "content": "你好小智"})
    llm_responses = llm.response("test", dialogue)
    response_message = []
    first_text = None
    start = 0

    for content in llm_responses:
        response_message.append(content)

        if is_segment(response_message):
            segment_text = "".join(response_message[start:])
            segment_text = get_string_no_punctuation_or_emoji(segment_text)
            if len(segment_text) > 0:
                if first_text is None:
                    first_text = segment_text
                    print("大模型首次返回耗时：" + str(datetime.now() - start_time))
                start = len(response_message)

    print("大模型返回总耗时：" + str(datetime.now() - start_time))
