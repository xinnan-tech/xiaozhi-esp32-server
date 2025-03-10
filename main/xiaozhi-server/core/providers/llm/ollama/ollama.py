from config.logger import setup_logging
from openai import OpenAI
import json
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")
        # Initialize OpenAI client with Ollama base URL
        #如果没有v1，增加v1
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"
            
        self.client = OpenAI(
            base_url=self.base_url,
            api_key="ollama"  # Ollama doesn't need an API key but OpenAI client requires one
        )

    def response(self, session_id, dialogue):
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            
            for chunk in responses:
                try:
                    delta = chunk.choices[0].delta if getattr(chunk, 'choices', None) else None
                    content = delta.content if hasattr(delta, 'content') else ''
                    if content:
                        yield content
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing chunk: {e}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama response generation: {e}")
            yield "【Ollama服务响应异常】"

    def response_with_functions(self, session_id, dialogue, functions=None):
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True,
                tools=functions,
            )
            
            current_function_call = None
            current_content = ""
            
            for chunk in stream:
                delta = chunk.choices[0].delta
                
                if delta.content:
                    current_content += delta.content
                    yield {"type": "content", "content": delta.content}
                
                if delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    # Handle the function call data using proper attribute access
                    if not current_function_call:
                        current_function_call = {
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
            
            if current_function_call:
                logger.bind(tag=TAG).debug(f"ollama Function call detected: {current_function_call}")
                yield {"type": "function_call", "function_call": current_function_call}

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama function call: {e}")
            yield {"type": "content", "content": f"【Ollama服务响应异常: {str(e)}】"}