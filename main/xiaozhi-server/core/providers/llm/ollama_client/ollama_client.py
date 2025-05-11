from config.logger import setup_logging
from ollama import Client
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
   
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")        
        self.client = Client(self.base_url) 
    def response(self, session_id, dialogue):
        try:
            responses = self.client.chat(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            for chunk in responses:
                try:                    
                    if chunk.message.content:
                        content = chunk.message.content
                        yield content
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing chunk: {e}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama response generation: {e}")
            yield "【Ollama服务响应异常】"
    def response_with_functions(self, session_id, dialogue, functions=None):
        try:
            stream = self.client.chat(
                model=self.model_name,
                messages=dialogue,
                stream=True,
                tools=functions,
            )

            logger.bind(tag=TAG).info(f"msg: {dialogue}")

            response_text = ""
            for chunk in stream:         
                if chunk.message.content:
                    content = chunk.message.content
                    response_text += content
            yield response_text, None

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama function call: {e}")
            yield f"【Ollama服务响应异常: {str(e)}】", None

