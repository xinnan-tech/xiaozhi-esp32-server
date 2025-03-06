from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class MemoryProviderBase(ABC):
    def __init__(self, config):
        self.config = config
        self.role_id = None
        self.llm = None

    @abstractmethod
    async def save_memory(self, msgs):
        """Save a new memory for specific role and return memory ID"""
        print("this is base func", msgs)

    @abstractmethod
    async def query_memory(self, query: str) -> str:
        """Query memories for specific role based on similarity"""
        return "please implement query method"

    def set_role_id(self, role_id: str):
        self.role_id = role_id    

    def set_llm(self, llm):
        self.llm = llm
        logger.bind(tag=TAG).debug("Set LLM for memory provider")