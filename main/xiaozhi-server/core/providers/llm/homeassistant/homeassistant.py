import requests
from requests.exceptions import RequestException
from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.agent_id = config.get("agent_id")  # Corresponding agent_id
        self.api_key = config.get("api_key")
        # Default to use base_url
        self.base_url = config.get("base_url", config.get("url"))
        # Concatenate complete API URL
        self.api_url = f"{self.base_url}/api/conversation/process"

    def response(self, session_id, dialogue, **kwargs):
        try:
            # Home Assistant voice assistant has built-in intents, no need to use xiaozhi ai's built-in ones, just pass what the user said to Home Assistant

            # Extract the content of the last message with role 'user'
            input_text = None
            if isinstance(dialogue, list):  # Ensure dialogue is a list
                # Iterate in reverse order to find the last message with role 'user'
                for message in reversed(dialogue):
                    if message.get("role") == "user":  # Find message with role 'user'
                        input_text = message.get("content", "")
                        break  # Exit loop immediately after finding

            # Construct request data
            payload = {
                "text": input_text,
                "agent_id": self.agent_id,
                "conversation_id": session_id,  # Use session_id as conversation_id
            }
            # Set request headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Send POST request
            response = requests.post(
                self.api_url, json=payload, headers=headers)

            # Check if request was successful
            response.raise_for_status()

            # Parse returned data
            data = response.json()
            speech = (
                data.get("response", {})
                .get("speech", {})
                .get("plain", {})
                .get("speech", "")
            )

            # Return generated content
            if speech:
                yield speech
            else:
                logger.bind(tag=TAG).warning(
                    "No speech content in API returned data")

        except RequestException as e:
            logger.bind(tag=TAG).error(f"HTTP request error: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error generating response: {e}")

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).error(
            f"Home Assistant does not support (function call), it is recommended to use other intent recognition methods"
        )