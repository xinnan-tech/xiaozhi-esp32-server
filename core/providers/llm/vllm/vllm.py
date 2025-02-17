import logging
import requests
import json
from core.providers.llm.base import LLMProviderBase

logger = logging.getLogger(__name__)

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        """
        初始化 vllm 提供器

        配置项包含：
          - model_name: 模型名称或路径（必填）
          - base_url: vllm 服务地址，默认为 "http://localhost:8000"
          - max_tokens: 最大生成 token 数量，默认为 256
          - temperature: 采样温度，默认为 0.7
        """
        self.model_name = config.get("model_name")
        if not self.model_name:
            raise ValueError("配置中必须指定 model_name")
        self.base_url = config.get("base_url", "http://localhost:8000")
        self.max_tokens = config.get("max_tokens", 256)
        self.temperature = config.get("temperature", 0.7)
    
    def response(self, session_id, dialogue):
        """
        根据对话生成 prompt，并调用 vllm 的 completions 接口，通过 HTTP POST 请求获取生成结果，
        返回生成的文本作为生成器

        参数：
          - session_id: 会话 ID（用于日志记录）
          - dialogue: 对话列表，每个元素为字典，包含 "role" 与 "content" 字段

        返回：
          生成器，每个元素为生成的文本
        """
        try:
            # 拼接对话日志，形成完整的 prompt
            prompt = ""
            for msg in dialogue:
                if msg["role"] == "system":
                    prompt += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    prompt += f"Assistant: {msg['content']}\n"

            # 根据 vllm 接口的 curl 示例，构造请求体参数
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            url = f"{self.base_url}/v1/completions"
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            json_response = response.json()

            # 根据返回格式解析生成文本
            # 如果返回结果遵循 OpenAI 的 completions 格式，则通常在 "choices" 列表中返回生成文本
            if "choices" in json_response and json_response["choices"]:
                generated_text = json_response["choices"][0].get("text", "")
                yield generated_text
            elif "response" in json_response:
                yield json_response["response"]
            elif "text" in json_response:
                yield json_response["text"]
            else:
                logger.error("无法解析 vllm 响应: %s", json_response)
                yield "【vllm 服务响应异常】"
        except Exception as e:
            logger.error("vllm 请求生成响应时发生错误: %s", e)
            yield "【vllm 服务响应异常】"