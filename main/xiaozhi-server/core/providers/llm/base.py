from abc import ABC, abstractmethod


class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, session_id, dialogue):
        """LLM response generator"""
        pass

    @abstractmethod
    def response_no_stream(self, system_prompt, user_prompt):
        pass