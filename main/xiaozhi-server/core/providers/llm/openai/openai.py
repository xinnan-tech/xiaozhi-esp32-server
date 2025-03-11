import openai
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if 'base_url' in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        check_model_key("LLM", self.api_key)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, session_id, dialogue):
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            
            is_active = True
            for chunk in responses:
                try:
                    # 检查是否存在有效的choice且content不为空
                    delta = chunk.choices[0].delta if getattr(chunk, 'choices', None) else None
                    content = delta.content if hasattr(delta, 'content') else ''
                except IndexError:
                    content = ''
                if content:
                    # 处理标签跨多个chunk的情况
                    if '<think>' in content:
                        is_active = False
                        content = content.split('<think>')[0]
                    if '</think>' in content:
                        is_active = True
                        content = content.split('</think>')[-1]
                    if is_active:
                        yield content

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")

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
            self.logger.bind(tag=TAG).error(f"Error in function call streaming: {e}")
            yield {"type": "content", "content": f"【OpenAI服务响应异常: {e}】"}