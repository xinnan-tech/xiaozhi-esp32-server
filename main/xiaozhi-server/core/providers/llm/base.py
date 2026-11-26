from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class LLMProviderBase(ABC):
    # provider 发起 HTTP 请求时的默认超时（秒）
    DEFAULT_HTTP_TIMEOUT = 60
    DEFAULT_CONNECT_TIMEOUT = 10

    @classmethod
    def resolve_timeout(cls, config, default=None):
        """解析 provider 配置里的 HTTP 超时，返回 (连接超时, 读取超时)

        配置写在模型配置的 JSON 里：
          timeout: 60           连接和读取都用这个值
          connect_timeout: 10  连接超时单独设置

        之前不少 provider 用 requests 发请求时都没传 timeout，上游不响应时
        请求会一直挂着，设备侧表现为「服务无响应」，服务端对应的线程也一直被
        占着不放。这里统一给一个上限，取值非法时回退到默认值。
        """
        if not isinstance(config, dict):
            config = {}

        def _positive(value, fallback):
            try:
                value = float(value)
            except (TypeError, ValueError):
                return fallback
            if value <= 0:
                return fallback
            return value

        fallback = float(default if default is not None else cls.DEFAULT_HTTP_TIMEOUT)
        read_timeout = _positive(config.get("timeout"), fallback)
        connect_timeout = _positive(
            config.get("connect_timeout"), float(cls.DEFAULT_CONNECT_TIMEOUT)
        )
        return (connect_timeout, read_timeout)

    @abstractmethod
    def response(self, session_id, dialogue):
        """LLM response generator"""
        pass

    def response_no_stream(self, system_prompt, user_prompt, **kwargs):
        # 构造对话格式
        dialogue = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        result = ""
        for part in self.response("", dialogue, **kwargs):
            result += part
        return result
    
    def response_with_functions(self, session_id, dialogue, functions=None):
        """
        Default implementation for function calling (streaming)
        This should be overridden by providers that support function calls

        Returns: generator that yields either text tokens or a special function call token
        """
        # For providers that don't support functions, just return regular response
        for token in self.response(session_id, dialogue):
            yield token, None

