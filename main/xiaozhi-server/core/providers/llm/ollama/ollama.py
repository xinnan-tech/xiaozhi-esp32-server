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
        # 如果没有v1，增加v1
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
            is_active=True
            for chunk in responses:
                try:
                    delta = chunk.choices[0].delta if getattr(chunk, 'choices', None) else None
                    content = delta.content if hasattr(delta, 'content') else ''
                    if content:
                        if '<think>' in content:
                            is_active = False
                            content = content.split('<think>')[0]
                        if '</think>' in content:
                            is_active = True
                            content = content.split('</think>')[-1]
                        if is_active:
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

            for chunk in stream:
                yield chunk.choices[0].delta.content, chunk.choices[0].delta.tool_calls

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama function call: {e}")
            yield f"【Ollama服务响应异常: {str(e)}】", None
