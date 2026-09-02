import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        timeout = config.get("timeout", 300)
        self.timeout = int(timeout) if timeout else 300
        self.num_ctx = config.get("num_ctx")
        self.options = config.get("options", {})
        if self.num_ctx:
            self.options["num_ctx"] = int(self.num_ctx)
        self.extra_body_config = config.get("extra_body", {})

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

        self.max_retries = int(config.get("max_retries", 2))

        logger.debug(
            f"LLM initialization: {self.model_name}, timeout={self.timeout}s, max_retries={self.max_retries}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        
        self.client = openai.OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url, 
            timeout=httpx.Timeout(self.timeout),
            max_retries=self.max_retries
        )

    @staticmethod
    def normalize_dialogue(dialogue):
        """Automatically fix missing content in dialogue messages"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue

    def response(self, session_id, dialogue, **kwargs):
        try:
            dialogue = self.normalize_dialogue(dialogue)

            request_params = {
                "model": self.model_name,
                "messages": dialogue,
                "stream": True,
            }

            # Prepare extra_body, starting with generic extra_body from config
            final_extra_body = getattr(self, "extra_body_config", {}).copy()
            
            # Merge in self.options (which includes num_ctx)
            if self.options:
                if "options" not in final_extra_body:
                    final_extra_body["options"] = {}
                # self.options take precedence over generic config if distinct, 
                # but usually self.options ARE from config, so update is fine.
                final_extra_body["options"].update(self.options)
            
            if final_extra_body:
                request_params["extra_body"] = final_extra_body
            
            # Add optional parameters, only add if parameter is not None
            optional_params = {
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "response_format": kwargs.get("response_format"),
            }

            for key, value in optional_params.items():
                if value is not None:
                    request_params[key] = value


            
            # Support for checking num_ctx in config (passed via self.xxx if we add it to init)
            # We need to add it to init first, or just check config again? 
            # Better to check if we can access config. config is passed to init.
            # We should update init to read num_ctx.
            
            # Wait, I cannot edit init in this same tool call easily if I am targeting line 81.
            # I will assume I need to do 2 edits or one big edit.
            # For now, let's just use getattr(self, 'num_ctx', None) and assume I added it to init.
            
            extra_body = {}
            if getattr(self, "num_ctx", None):
                 # Ollama uses "options" for parameters in the OpenAI endpoint often,
                 # BUT some versions mapping allow "num_ctx" at top level of extra_body??
                 # "options" is the safest for Ollama native parameters.
                 extra_body["options"] = {"num_ctx": int(self.num_ctx)}
            
            # Standard OpenAI SDK per-request timeout
            request_timeout = kwargs.get("timeout", self.timeout)
            request_retries = kwargs.get("max_retries", self.max_retries)

            responses = self.client.with_options(max_retries=request_retries).chat.completions.create(
                **request_params,
                timeout=request_timeout
            )

            is_active = True
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

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        try:
            dialogue = self.normalize_dialogue(dialogue)

            request_params = {
                "model": self.model_name,
                "messages": dialogue,
                "stream": True,
                "tools": functions,
            }

            if self.options:
                request_params["extra_body"] = {"options": self.options}

            optional_params = {
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            }

            for key, value in optional_params.items():
                if value is not None:
                    request_params[key] = value

            # Standard OpenAI SDK per-request timeout
            request_timeout = kwargs.get("timeout", self.timeout)
            request_retries = kwargs.get("max_retries", self.max_retries)

            stream = self.client.with_options(max_retries=request_retries).chat.completions.create(
                **request_params,
                timeout=request_timeout
            )

            for chunk in stream:
                if getattr(chunk, "choices", None):
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "")
                    tool_calls = getattr(delta, "tool_calls", None)
                    yield content, tool_calls
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    usage_info = getattr(chunk, "usage", None)
                    logger.bind(tag=TAG).info(
                        f"Token usage: Input {getattr(usage_info, 'prompt_tokens', 'Unknown')}, "
                        f"Output {getattr(usage_info, 'completion_tokens', 'Unknown')}, "
                        f"Total {getattr(usage_info, 'total_tokens', 'Unknown')}"
                    )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in function call streaming: {e}")
            yield f"【OpenAI Service Response Exception: {e}】", None
