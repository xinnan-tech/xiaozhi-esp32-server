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
        # 增加timeout的配置项，单位为秒
        timeout = config.get("timeout", 300)
        self.timeout = int(timeout) if timeout else 300

        param_defaults = {
            "max_tokens": (500, int),
            "temperature": (0.7, lambda x: round(float(x), 1)),
            "top_p": (1.0, lambda x: round(float(x), 1)),
            "frequency_penalty": (0, lambda x: round(float(x), 1)),
        }

        for param, (default, converter) in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self,
                    param,
                    converter(value) if value not in (None, "") else default,
                )
            except (ValueError, TypeError):
                setattr(self, param, default)

        logger.debug(
            f"意图识别参数初始化: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=httpx.Timeout(self.timeout))

    def response(self, session_id, dialogue, **kwargs):
        """
        同步流式响应方法
        注意：保持同步以兼容基类和其他 LLM 提供商
        """
        try:
            # Create streaming response
            # 注意：ChatGLM 等服务可能不支持 responses.create API，改用标准的 chat.completions.create
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
            )
            
            is_active = True
            
            for chunk in stream:
                try:
                    # Handle response choices
                    if not hasattr(chunk, "choices") or not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", None)
                    
                    if content is None:
                        continue
                    
                    # Handle thinking tags (for reasoning models like o1)
                    # Filter out content between <think>...</think>
                    if "<think>" in content:
                        is_active = False
                        content = content.split("<think>")[0]
                    if "</think>" in content:
                        is_active = True
                        content = content.split("</think>")[-1]
                    if is_active:
                        yield content
                        
                except (IndexError, AttributeError) as e:
                    continue
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理 chunk 时发生未预期错误: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}", exc_info=True)

    def response_with_functions(self, session_id, dialogue, functions=None):
        """
        同步流式响应方法（支持函数调用）
        注意：保持同步以兼容基类和其他 LLM 提供商
        """
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_name,
                "messages": dialogue,
                "stream": True,
            }
            
            # Add tools/functions if provided
            if functions:
                request_params["tools"] = functions
                
            # Create streaming response (同步版本，移除 await)
            stream = self.client.chat.completions.create(**request_params)

            for chunk in stream:
                try:
                    # Handle token usage reporting
                    if hasattr(chunk, "usage") and isinstance(chunk.usage, CompletionUsage):
                        usage_info = chunk.usage
                        logger.bind(tag=TAG).info(
                            f"Token 消耗：输入 {getattr(usage_info, 'prompt_tokens', '未知')}，"
                            f"输出 {getattr(usage_info, 'completion_tokens', '未知')}，"
                            f"共计 {getattr(usage_info, 'total_tokens', '未知')}"
                        )
                        continue
                    
                    # Handle response choices
                    if not hasattr(chunk, "choices") or not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Extract content and tool calls
                    content = getattr(delta, "content", None)
                    tool_calls = getattr(delta, "tool_calls", None)
                    
                    # Yield the chunk
                    yield content, tool_calls
                    
                except (IndexError, AttributeError) as e:
                    continue

        except openai.APIError as e:
            error_msg = f"OpenAI API error: {e.message if hasattr(e, 'message') else str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield f"【API错误: {error_msg}】", None
            
        except openai.APIConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield f"【连接错误: 无法连接到服务】", None
            
        except openai.RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield f"【请求过于频繁，请稍后再试】", None
            
        except Exception as e:
            error_msg = f"Unexpected error in function calling: {type(e).__name__}: {str(e)}"
            logger.bind(tag=TAG).error(error_msg, exc_info=True)
            yield f"【OpenAI服务响应异常: {str(e)}】", None

    async def response_stream(
        self,
        chat_ctx: ChatContext,
        **kwargs: Any
    ) -> AsyncGenerator[ChatChunk, None]:
        """
        New streaming interface using standard protocol
        
        This method implements the new standard interface defined in LLMProviderBase.
        It uses:
        - ChatContext as input (standard dialogue protocol)
        - ChatChunk as output (standard streaming protocol)
        - OpenAI Responses API (modern response.create)
        
        Args:
            chat_ctx: Standard ChatContext with dialogue history
            **kwargs: Additional options:
                - max_output_tokens: Override max tokens
                - temperature: Override temperature
                - top_p: Override top_p
                - frequency_penalty: Override frequency penalty
        
        Yields:
            ChatChunk: Standardized streaming chunks with deltas and usage
        
        Example:
            async for chunk in provider.response_stream(chat_ctx):
                if chunk.delta and chunk.delta.content:
                    print(chunk.delta.content)
                if chunk.usage:
                    print(f"Tokens: {chunk.usage.total_tokens}")
        """
        try:
            # 1. Convert ChatContext to OpenAI format
            messages, _ = chat_ctx.to_provider_format(format="openai")
            
            logger.bind(tag=TAG).debug(
                f"Starting streaming with model={self.model_name}, "
                f"messages_count={len(messages)}"
            )
            
            # 2. Prepare request parameters
            max_output_tokens = kwargs.get("max_output_tokens", self.max_output_tokens)
            temperature = kwargs.get("temperature", self.temperature)
            top_p = kwargs.get("top_p", self.top_p)
            frequency_penalty = kwargs.get("frequency_penalty", self.frequency_penalty)
            
            # 3. Call OpenAI Responses API
            # TODO: system instruction needs to be added
            stream: AsyncStream[ResponseStreamEvent] = await self.client.responses.create(
                input=messages,
                model=self.model_name,
                stream=True,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )
            
            # 4. Parse stream and yield ChatChunk (focus on output_item.done + completed)
            async for event in stream:
                try:
                    chunk = self._parse_response_event(event)
                    if chunk:
                        yield chunk
                except (IndexError, AttributeError) as e:
                    logger.bind(tag=TAG).debug(f"Skipping malformed event: {e}")
                    continue
            
            logger.bind(tag=TAG).debug("Stream completed successfully")
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {e.message if hasattr(e, 'message') else str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            # Yield error chunk
            yield ChatChunk(
                delta=ChatDelta(
                    role="assistant",
                    content=f"【API错误: {error_msg}】"
                )
            )
            
        except openai.APIConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield ChatChunk(
                delta=ChatDelta(
                    role="assistant",
                    content="【连接错误: 无法连接到服务】"
                )
            )
            
        except openai.RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield ChatChunk(
                delta=ChatDelta(
                    role="assistant",
                    content="【请求过于频繁，请稍后再试】"
                )
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            yield ChatChunk(
                delta=ChatDelta(
                    role="assistant",
                    content=f"【服务异常: {str(e)}】"
                )
            )
