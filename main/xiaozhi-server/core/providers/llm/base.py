from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, session_id, dialogue):
        """LLM response generator"""
        pass

    def response_no_stream(self, system_prompt, user_prompt):
        try:
            # 构造对话格式
            dialogue = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            result = ""
            for part in self.response("", dialogue):
                result += part
            return result

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama response generation: {e}")
            return "【LLM服务响应异常】"