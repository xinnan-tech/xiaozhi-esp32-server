import logging
import requests
import json
from core.providers.llm.base import LLMProviderBase

logger = logging.getLogger(__name__)

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        """
        初始化 vllm 聊天提供器

        配置项：
          - model_name: 模型名称或路径（必填）
          - base_url: vllm 服务地址，默认为 "http://localhost:8000"
        """
        self.model_name = config.get("model_name")
        if not self.model_name:
            raise ValueError("配置中必须指定 model_name")
        
        self.base_url = config.get("base_url", "http://localhost:8000")
        
    def response(self, session_id, dialogue):
        """
        根据对话消息构造请求（消息格式：{"role": "xxx", "content": "xxx"}），
        调用 vllm 的聊天接口，并返回生成的响应文本。

        参数：
          - session_id: 会话 ID（用于日志记录）
          - dialogue: 消息列表，每个元素为字典，例如:
                      {"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": "Who won the world series in 2020?"}

        返回：
          一个生成器，产生生成的文本（取第一个候选消息的 "content"）。
        """
        try:
            # 直接使用 dialogue 列表作为 chat 接口的 messages 字段
            payload = {
                "model": self.model_name,
                "messages": dialogue
            }

            url = f"{self.base_url}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            json_response = response.json()

            # 假设响应格式类似 OpenAI chat completions 的结构
            # 从 "choices" 数组中取第一个候选消息的 "message" 字段的 "content"
            if "choices" in json_response and json_response["choices"]:
                generated_message = json_response["choices"][0].get("message", {})
                content = generated_message.get("content", "")
                yield content
            else:
                logger.error("无法解析 vllm 响应: %s", json_response)
                yield "【vllm 服务响应异常】"
        except Exception as e:
            logger.error("vllm 聊天响应生成请求错误: %s", e)
            yield "【vllm 服务响应异常】"