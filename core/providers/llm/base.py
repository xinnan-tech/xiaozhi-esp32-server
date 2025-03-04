from abc import ABC, abstractmethod


class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, session_id, dialogue):
        """LLM response generator"""
        pass
