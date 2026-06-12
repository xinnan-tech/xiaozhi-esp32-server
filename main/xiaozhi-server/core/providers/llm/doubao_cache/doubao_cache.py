"""
豆包（火山方舟）Session 缓存 LLM Provider

混合模式设计：
- 普通对话：使用 Responses API + previous_response_id，享受 Session 缓存
- 工具调用：使用 Chat Completions API，稳定支持 tools + streaming

Session 缓存原理：
首轮请求通过 Chat Completions API 发送完整对话，获取 response_id。
后续轮次通过 Responses API + previous_response_id 发送，
服务端自动复用已缓存的上下文，减少重复计算和 Token 传输。

配置示例：
  DoubaoCacheLLM:
    type: doubao_cache
    base_url: https://ark.cn-beijing.volces.com/api/v3
    model_name: doubao-seed-2-0-lite-260215
    api_key: xxx
    cache:
      enabled: true
      expire_seconds: 86400  # 缓存过期时间（秒），最长 7 天
"""
import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase
from typing import Dict

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url", "https://ark.cn-beijing.volces.com/api/v3")

        timeout_config = config.get("timeout")
        if isinstance(timeout_config, dict):
            custom_timeout = httpx.Timeout(
                pool=timeout_config.get("pool", 2.0),
                connect=timeout_config.get("connect", 3.0),
                write=timeout_config.get("write", 5.0),
                read=timeout_config.get("read", 60.0)
            )
        elif isinstance(timeout_config, (int, float)) and timeout_config > 0:
            custom_timeout = httpx.Timeout(timeout_config)
        else:
            custom_timeout = httpx.Timeout(300)

        param_defaults = {
            "max_tokens": int,
            "temperature": lambda x: round(float(x), 1),
            "top_p": lambda x: round(float(x), 1),
            "frequency_penalty": lambda x: round(float(x), 1),
        }
        for param, converter in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self, param,
                    converter(value) if value not in (None, "") else None,
                )
            except (ValueError, TypeError):
                setattr(self, param, None)

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=custom_timeout,
        )

        # 缓存配置（支持 boolean 开关和 dict 详细配置）
        self._cache_config = config.get("cache", {})
        if isinstance(self._cache_config, bool):
            self._cache_enabled = self._cache_config
        elif isinstance(self._cache_config, dict):
            self._cache_enabled = self._cache_config.get("enabled", True)
        else:
            self._cache_enabled = True

        # Session 状态：session_id -> response_id
        self._session_response_ids: Dict[str, str] = {}

    @staticmethod
    def normalize_dialogue(dialogue):
        """自动修复 dialogue 中缺失 content 的消息"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue

    def response(self, session_id, dialogue, **kwargs):
        """普通对话：优先使用 Responses API Session 缓存，失败回退到 Chat Completions"""
        dialogue = self.normalize_dialogue(dialogue)

        if self._cache_enabled:
            prev_id = self._session_response_ids.get(session_id)
            if prev_id:
                try:
                    yield from self._stream_with_session(session_id, dialogue, prev_id, **kwargs)
                    return
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"Session 缓存请求失败，回退到 Chat Completions: {e}"
                    )
                    self._session_response_ids.pop(session_id, None)

        # 首轮或缓存失效/关闭：使用 Chat Completions API
        yield from self._stream_chat_completions(session_id, dialogue, **kwargs)

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        """工具调用：始终使用 Chat Completions API（稳定支持 tools + streaming）"""
        dialogue = self.normalize_dialogue(dialogue)

        request_params = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
            "tools": functions,
        }

        optional_params = {
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
        }
        for key, value in optional_params.items():
            if value is not None:
                request_params[key] = value

        # 禁用思考模式
        request_params.setdefault("extra_body", {}).update(
            {"thinking": {"type": "disabled"}}
        )

        stream = self.client.chat.completions.create(**request_params)

        try:
            for chunk in stream:
                if getattr(chunk, "choices", None):
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "")
                    tool_calls = getattr(delta, "tool_calls", None)
                    yield content, tool_calls
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    self._log_usage(getattr(chunk, "usage", None))
        finally:
            stream.close()

    def _stream_with_session(self, session_id, dialogue, prev_id, **kwargs):
        """使用 Responses API + previous_response_id 进行 Session 缓存流式对话"""
        # 提取最新用户消息
        last_user_msg = None
        for msg in reversed(dialogue):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        if not last_user_msg:
            raise ValueError("未找到用户消息")

        logger.bind(tag=TAG).info(
            f"使用 Session 缓存: session_id={session_id}, prev_response_id={prev_id[:20]}..."
        )

        stream = self.client.responses.create(
            model=self.model_name,
            input=[{"role": "user", "content": last_user_msg}],
            previous_response_id=prev_id,
            stream=True,
            store=True,
            extra_body={
                "caching": {"type": "enabled"},
                "thinking": {"type": "disabled"},
            },
        )

        response_id = None
        try:
            for event in stream:
                # 捕获 response ID
                if hasattr(event, "id") and event.id:
                    response_id = event.id

                # 解析流式输出事件
                text = self._parse_responses_stream_event(event)
                if text:
                    # 过滤思考标签
                    yield text
        finally:
            if response_id:
                self._session_response_ids[session_id] = response_id
                logger.bind(tag=TAG).info(
                    f"Session 缓存已更新: session_id={session_id}, "
                    f"new_response_id={response_id[:20]}..."
                )
            stream.close()

    def _stream_chat_completions(self, session_id, dialogue, **kwargs):
        """标准 Chat Completions API 流式对话（首轮或回退路径）"""
        request_params = {"model": self.model_name, "messages": dialogue, "stream": True}
        optional_params = {
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
        }
        for key, value in optional_params.items():
            if value is not None:
                request_params[key] = value
        request_params.setdefault("extra_body", {}).update({"thinking": {"type": "disabled"}})
        responses = self.client.chat.completions.create(**request_params)
        try:
            for chunk in responses:
                try:
                    delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None
                    content = getattr(delta, "content", "") if delta else ""
                except IndexError:
                    content = ""
                if content:
                    yield content
        finally:
            responses.close()



    @staticmethod
    def _parse_responses_stream_event(event):
        """解析 Responses API 流式事件，提取文本内容

        Responses API 的流式事件格式与 Chat Completions 不同，
        需要根据事件类型提取 output 中的 text content。
        """
        # 处理 response.output_text.delta 类型事件
        if hasattr(event, "type") and event.type == "response.output_text.delta":
            return getattr(event, "delta", "")
        # 处理 response.completed 事件中的完整输出
        if hasattr(event, "type") and event.type == "response.completed":
            return None
        # 兼容：尝试从 output 提取
        output = getattr(event, "output", None)
        if output:
            for item in (output if isinstance(output, list) else [output]):
                content_list = getattr(item, "content", None)
                if content_list:
                    for c in (content_list if isinstance(content_list, list) else [content_list]):
                        text = getattr(c, "text", None)
                        if text:
                            return text
        return None

    def _log_usage(self, usage_info):
        """记录 Token 使用量，包含缓存命中信息"""
        prompt_tokens = getattr(usage_info, "prompt_tokens", "未知")
        completion_tokens = getattr(usage_info, "completion_tokens", "未知")
        total_tokens = getattr(usage_info, "total_tokens", "未知")

        # Chat Completions API 的缓存信息
        details = getattr(usage_info, "prompt_tokens_details", None)
        cached_tokens = getattr(details, "cached_tokens", 0) if details else 0
        cache_created = getattr(details, "cache_creation_input_tokens", 0) if details else 0

        # Responses API 的缓存信息
        input_details = getattr(usage_info, "input_tokens_details", None)
        if input_details and not cached_tokens:
            cached_tokens = getattr(input_details, "cached_tokens", 0)

        cache_log = ""
        if cached_tokens or cache_created:
            cache_log = f"，缓存命中 {cached_tokens}，缓存创建 {cache_created}"

        logger.bind(tag=TAG).info(
            f"Token 消耗：输入 {prompt_tokens}，输出 {completion_tokens}，"
            f"共计 {total_tokens}{cache_log}"
        )

    def clear_session(self, session_id):
        """清理指定会话的缓存状态"""
        removed = self._session_response_ids.pop(session_id, None)
        if removed:
            logger.bind(tag=TAG).info(f"已清理 Session 缓存: session_id={session_id}")
