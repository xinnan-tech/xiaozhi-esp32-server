from config.logger import setup_logging
import requests, json
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):

        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")

    def response(self, session_id, dialogue):        
        try:
            # Convert dialogue format to Ollama format
            prompt = ""
            for msg in dialogue:
                if msg["role"] == "system":
                    prompt += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    prompt += f"Assistant: {msg['content']}\n"

            # Make request to Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            )
            is_active=True
            for line in response.iter_lines():
                content=''
                if line:
                    json_response = json.loads(line)
                    if "response" in json_response:
                        content=json_response["response"]
                        if '<think>' in content:
                            is_active = False
                            content = content.split('<think>')[0]
                        if '</think>' in content:
                            is_active = True
                            content = content.split('</think>')[-1]
                        if is_active:
                            yield content


        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Ollama response generation: {e}")
            yield "【Ollama服务响应异常】"
