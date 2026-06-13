import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase
from urllib.parse import urlparse

TAG = __name__
logger = setup_logging()

# 需要禁用思考模式的平台域名及其对应参数（默认关闭思考模式）
THINKING_DISABLED_DOMAINS = {
    "aliyuncs.com": {"enable_thinking": False},
    "bigmodel.cn": {"thinking": {"type": "disabled"}},
    "moonshot.cn": {"thinking": {"type": "disabled"}},
    "volces.com": {"thinking": {"type": "disabled"}},
}


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        
        timeout_config = config.get("timeout")
        if isinstance(timeout_config, dict):
            # 细粒度超时配置
            custom_timeout = httpx.Timeout(
                pool=timeout_config.get("pool", 2.0),
                connect=timeout_config.get("connect", 3.0),
                write=timeout_config.get("write", 5.0),
                read=timeout_config.get("read", 60.0)
            )
        elif isinstance(timeout_config, (int, float)) and timeout_config > 0:
            # 兼容旧的单一超时配置（整数或浮点数）
            custom_timeout = httpx.Timeout(timeout_config)
        else:
            # 未配置或配置无效，使用默认值
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
                    self,
                    param,
                    converter(value) if value not in (None, "") else None,
                )
            except (ValueError, TypeError):
                setattr(self, param, None)

        logger.debug(
            f"意图识别参数初始化: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=custom_timeout)

        # 缓存控制（千问显式缓存）
        self._cache_config = config.get("cache", {})
        self._cache_enabled = self._detect_cache_enabled()

    @staticmethod
    def normalize_dialogue(dialogue):
        """自动修复 dialogue 中缺失 content 的消息"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue

    def _detect_cache_enabled(self):
        """检测是否启用显式缓存（千问 cache_control）

        支持两种配置方式：
        - boolean: cache: true/false（智控台开关）
        - dict: cache: {enabled: true/false}（YAML 手动配置）
        """
        cache = self._cache_config
        # boolean 直传：cache: true
        if isinstance(cache, bool):
            return cache
        # dict 格式：cache: {enabled: true}
        if isinstance(cache, dict) and "enabled" in cache:
            return cache["enabled"]
        # 自动检测：DashScope 域名默认开启
        if self.base_url and "aliyuncs.com" in self.base_url:
            return True
        return False

    def _apply_cache_control(self, dialogue):
        """为静态 system 消息添加 cache_control 标记（千问显式缓存）

        将第一条 system 消息的 content 从字符串转为数组格式，
        加入 cache_control: {"type": "ephemeral"} 标记，
        使该静态前缀在千问 API 端被缓存，5 分钟内命中后按 10% 输入价计费。
        """
        if not self._cache_enabled:
            return dialogue
        if not dialogue or dialogue[0].get("role") != "system":
            return dialogue

        dialogue = [dict(m) for m in dialogue]  # 浅拷贝，不污染原始数据
        content = dialogue[0].get("content", "")
        if isinstance(content, str) and content:
            dialogue[0] = {
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": content,
                    "cache_control": {"type": "ephemeral"}
                }]
            }
        return dialogue

    def _apply_thinking_disabled(self, request_params: dict):
        """根据域名自动禁用思考模式"""
        parsed_url = urlparse(self.base_url)
        domain = parsed_url.netloc
        for disabled_domain, params in THINKING_DISABLED_DOMAINS.items():
            if disabled_domain in domain:
                request_params.setdefault("extra_body", {}).update(params)
                logger.bind(tag=TAG).info(f"为域名 {domain} 禁用思考模式，参数: {params}")
                break

    def response(self, session_id, dialogue, **kwargs):
        dialogue = self.normalize_dialogue(dialogue)
        dialogue = self._apply_cache_control(dialogue)

        request_params = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
        }

        # 添加可选参数,只有当参数不为None时才添加
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
        self._apply_thinking_disabled(request_params)

        responses = self.client.chat.completions.create(**request_params)

        is_active = True
        try:            
            for chunk in responses:
                try:
                    delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None
                    content = getattr(delta, "content", "") if delta else ""
                except IndexError:
                    content = ""
                if content:
                    if "<think>" in content:
                        is_active = False
                        content = content.split("<think>")[0]
                    if "</think>" in content:
                        is_active = True
                        content = content.split("</think>")[-1]
                    if is_active:
                        yield content
        finally:
            responses.close()

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        dialogue = self.normalize_dialogue(dialogue)
        dialogue = self._apply_cache_control(dialogue)

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
        self._apply_thinking_disabled(request_params)

        stream = self.client.chat.completions.create(**request_params)

        try:
            for chunk in stream:
                if getattr(chunk, "choices", None):
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "")
                    tool_calls = getattr(delta, "tool_calls", None)
                    yield content, tool_calls
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    usage_info = getattr(chunk, "usage", None)
                    prompt_tokens = getattr(usage_info, 'prompt_tokens', '未知')
                    completion_tokens = getattr(usage_info, 'completion_tokens', '未知')
                    total_tokens = getattr(usage_info, 'total_tokens', '未知')
                    # 提取缓存命中信息
                    details = getattr(usage_info, 'prompt_tokens_details', None)
                    cached_tokens = getattr(details, 'cached_tokens', 0) if details else 0
                    cache_created = getattr(details, 'cache_creation_input_tokens', 0) if details else 0
                    cache_log = ""
                    if cached_tokens or cache_created:
                        cache_log = f"，缓存命中 {cached_tokens}，缓存创建 {cache_created}"
                    logger.bind(tag=TAG).info(
                        f"Token 消耗：输入 {prompt_tokens}，输出 {completion_tokens}，"
                        f"共计 {total_tokens}{cache_log}"
                    )
        finally:
            stream.close()
