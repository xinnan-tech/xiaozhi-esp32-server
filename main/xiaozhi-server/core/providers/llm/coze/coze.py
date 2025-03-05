from config.logger import setup_logging
import requests
import json
import re
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()

# 定义用于匹配中文标点符号的正则表达式（包括句号、感叹号、问号、分号）
punctuation_pattern = re.compile(r'([。！？；])')

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.personal_access_token = config.get("personal_access_token")
        self.bot_id = config.get("bot_id")
        self.user_id = config.get("user_id")  # 默认用户 ID
        self.base_url = config.get("base_url")

    def response(self, session_id, dialogue):
        try:
            # 从对话中取出最新的用户消息
            last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")
            data = {
                "conversation_id": session_id,
                "bot_id": self.bot_id,
                "user": self.user_id,
                "query": last_msg["content"],
                "stream": True
            }
            logger.bind(tag=TAG).info(f"发送到 Coze API 的请求数据: {json.dumps(data, ensure_ascii=False)}")
            
            headers = {
                'Authorization': f'Bearer {self.personal_access_token}',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Host': 'api.coze.cn',
                'Connection': 'keep-alive'
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                stream=True
            )
            logger.bind(tag=TAG).info(f"请求状态: {response.status_code}")
            
            if response.status_code == 200:
                # 对每一行流数据进行处理，不做跨块累积
                for line_bytes in response.iter_lines(decode_unicode=False):
                    if not line_bytes:
                        continue
                    try:
                        # 使用 utf-8 解码，错误部分用替换符
                        line = line_bytes.decode('utf-8', errors='replace')
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"解码失败: {e}")
                        continue
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_chunk = json.loads(data_str)
                        except json.JSONDecodeError as e:
                            logger.bind(tag=TAG).error(f"JSON解析失败: {e} 数据: {line}")
                            continue
                        msg = data_chunk.get("message", {})
                        if msg.get("role") == "assistant" and msg.get("type") == "answer":
                            content = msg.get("content", "")
                            # 如果返回内容中包含标点符号，则按标点拆分，立即返回每个片段
                            if punctuation_pattern.search(content):
                                # 利用 finditer 找到每个标点，并返回以标点结尾的片段
                                start = 0
                                for match in punctuation_pattern.finditer(content):
                                    end = match.end()
                                    sentence = content[start:end].strip()
                                    if sentence:
                                        yield sentence
                                    start = end
                                # 如果拆分后剩余内容也返回（不含标点），直接返回
                                if start < len(content):
                                    remainder = content[start:].strip()
                                    if remainder:
                                        yield remainder
                            else:
                                # 如果没有标点，则直接返回这块内容
                                if content.strip():
                                    yield content.strip()
            else:
                logger.bind(tag=TAG).error(f"请求失败，状态码: {response.status_code}")
                yield f"【Coze服务响应异常：请求失败，状态码 {response.status_code}】"
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Coze response generation: {e}")
            yield "【Coze服务响应异常】"
