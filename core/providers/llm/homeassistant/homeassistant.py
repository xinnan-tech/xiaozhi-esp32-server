import requests
from requests.exceptions import RequestException
from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.agent_id = config.get("agent_id")  # 对应 agent_id
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", config.get("url"))  # 默认使用 base_url
        self.api_url = f"{self.base_url}/api/conversation/process"  # 拼接完整的 API URL

    def response(self, session_id, dialogue):
        print(dialogue)
        try:
            # home assistant语音助手自带意图，无需使用xiaozhi ai自带的，只需要把用户说的话传递给home assistant即可

            # 提取最后一个 role 为 'user' 的 content
            input_text = None
            if isinstance(dialogue, list):  # 确保 dialogue 是一个列表
                # 逆序遍历，找到最后一个 role 为 'user' 的消息
                for message in reversed(dialogue):
                    if message.get("role") == "user":  # 找到 role 为 'user' 的消息
                        input_text = message.get("content", "")
                        break  # 找到后立即退出循环

            # 构造请求数据
            payload = {
                "text": input_text,
                "agent_id": self.agent_id,
                "conversation_id": session_id  # 使用 session_id 作为 conversation_id
            }
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 发起 POST 请求
            response = requests.post(self.api_url, json=payload, headers=headers)

            # 检查请求是否成功
            response.raise_for_status()

            # 解析返回数据
            data = response.json()
            speech = data.get("response", {}).get("speech", {}).get("plain", {}).get("speech", "")

            # 返回生成的内容
            if speech:
                yield speech
            else:
                logger.bind(tag=TAG).warning("API 返回数据中没有 speech 内容")

        except RequestException as e:
            logger.bind(tag=TAG).error(f"HTTP 请求错误: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成响应时出错: {e}")
