import traceback
from ..base import MemoryProviderBase, logger
from mem0 import MemoryClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.api_version = config.get("api_version", "v1.1")
        
        # Debug logging for API key (show first/last 4 chars only for security)
        if self.api_key:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****"
            logger.bind(tag=TAG).debug(f"Mem0 API key configured: {masked_key} (length: {len(self.api_key)})")
        else:
            logger.bind(tag=TAG).warning("Mem0 API key is empty or not configured")
        
        model_key_msg = check_model_key("Mem0ai", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            logger.bind(tag=TAG).error(f"API key validation failed. Please check your Mem0 API key configuration.")
            self.use_mem0 = False
            return
        else:
            self.use_mem0 = True
            logger.bind(tag=TAG).debug("Mem0 API key passed initial validation")

        try:
            logger.bind(tag=TAG).debug(f"Attempting to connect to Mem0ai service with API version: {self.api_version}")
            self.client = MemoryClient(api_key=self.api_key)
            logger.bind(tag=TAG).info(
                "Successfully connected to Mem0ai service")
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error occurred while connecting to Mem0ai service: {str(e)}")
            logger.bind(tag=TAG).error(
                f"Detailed error: {traceback.format_exc()}")
            logger.bind(tag=TAG).error(
                "Please verify your API key at https://app.mem0.ai/dashboard/api-keys")
            self.use_mem0 = False

    async def save_memory(self, msgs):
        if not self.use_mem0:
            return None
        if len(msgs) < 2:
            return None

        try:
            # Format the content as a message list for mem0
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs
                if message.role != "system"
            ]
            result = self.client.add(
                messages, user_id=self.role_id, output_format=self.api_version
            )
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to save memory: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.use_mem0:
            return ""
        try:
            results = self.client.search(
                query, user_id=self.role_id, output_format=self.api_version
            )
            if not results or "results" not in results:
                return ""

            # Format each memory entry with its update time up to minutes
            memories = []
            for entry in results["results"]:
                timestamp = entry.get("updated_at", "")
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                memory = entry.get("memory", "")
                if timestamp and memory:
                    # Store tuple of (timestamp, formatted_string) for sorting
                    memories.append(
                        (timestamp, f"[{formatted_time}] {memory}"))

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Extract only the formatted strings
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to query memory: {str(e)}")
            return ""
