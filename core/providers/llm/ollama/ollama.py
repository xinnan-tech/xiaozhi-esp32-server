from config.logger import setup_logging
import openai
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        
        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://127.0.0.1:11434/v1")
        
        self.client = openai.OpenAI(api_key="ollama", base_url=self.base_url)

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