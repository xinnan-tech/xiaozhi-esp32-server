import traceback
import time
import asyncio
from ..base import MemoryProviderBase, logger
from mem0 import MemoryClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        logger.bind(tag=TAG).info("[MEM0-INIT] Initializing MEM0 memory provider")
        logger.bind(tag=TAG).info(f"[MEM0-INIT] Config received: {config}")
        
        self.api_key = config.get("api_key", "")
        self.api_version = config.get("api_version", "v1.1")
        
        # Debug logging for API key (show first/last 4 chars only for security)
        if self.api_key:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****"
            logger.bind(tag=TAG).info(f"[MEM0-INIT] API key configured: {masked_key} (length: {len(self.api_key)})")
        else:
            logger.bind(tag=TAG).error("[MEM0-INIT] API key is empty or not configured - MEM0 will be disabled")
        
        model_key_msg = check_model_key("Mem0ai", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(f"[MEM0-INIT] {model_key_msg}")
            logger.bind(tag=TAG).error(f"[MEM0-INIT] API key validation failed. Please check your Mem0 API key configuration.")
            self.use_mem0 = False
            return
        else:
            self.use_mem0 = True
            logger.bind(tag=TAG).info("[MEM0-INIT] API key passed initial validation")

        try:
            logger.bind(tag=TAG).info(f"[MEM0-INIT] Attempting to connect to Mem0ai service with API version: {self.api_version}")
            self.client = MemoryClient(api_key=self.api_key)
            logger.bind(tag=TAG).info(
                "[MEM0-INIT] Successfully connected to Mem0ai service - MEM0 is ENABLED")
            logger.bind(tag=TAG).info(f"[MEM0-INIT] role_id/user_id: {self.role_id}")
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"[MEM0-INIT] Error occurred while connecting to Mem0ai service: {str(e)}")
            logger.bind(tag=TAG).error(
                f"[MEM0-INIT] Detailed error: {traceback.format_exc()}")
            logger.bind(tag=TAG).error(
                "[MEM0-INIT] Please verify your API key at https://app.mem0.ai/dashboard/api-keys")
            self.use_mem0 = False

    async def save_memory(self, msgs):
        logger.bind(tag=TAG).info(f"[MEM0] save_memory called with {len(msgs) if msgs else 0} messages")
        
        if not self.use_mem0:
            logger.bind(tag=TAG).warning("[MEM0] Memory saving skipped - use_mem0 is False")
            return None
        if len(msgs) < 2:
            logger.bind(tag=TAG).info(f"[MEM0] Memory saving skipped - insufficient messages (got {len(msgs)}, need at least 2)")
            return None

        try:
            logger.bind(tag=TAG).info(f"[MEM0] Preparing to save memory for user_id: {self.role_id}")
            
            # Format the content as a message list for mem0
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs
                if message.role != "system"
            ]
            
            logger.bind(tag=TAG).info(f"[MEM0] Formatted {len(messages)} messages for saving (excluded system messages)")
            logger.bind(tag=TAG).debug(f"[MEM0] Messages to save: {messages[:2]}...")  # Log first 2 messages for debugging
            
            logger.bind(tag=TAG).info(f"[MEM0] Calling client.add() with API version: {self.api_version}")
            result = self.client.add(
                messages, user_id=self.role_id, output_format=self.api_version
            )
            
            logger.bind(tag=TAG).info(f"[MEM0] Memory saved successfully! Result: {result}")
            logger.bind(tag=TAG).debug(f"[MEM0] Full save memory result: {result}")
            return result
        except Exception as e:
            logger.bind(tag=TAG).error(f"[MEM0] Failed to save memory: {str(e)}")
            logger.bind(tag=TAG).error(f"[MEM0] Exception type: {type(e).__name__}")
            logger.bind(tag=TAG).error(f"[MEM0] Full traceback: {traceback.format_exc()}")
            return None

    async def query_memory(self, query: str) -> str:
        logger.bind(tag=TAG).info(f"[MEM0-QUERY] query_memory called with query: {query[:100]}...")
        
        if not self.use_mem0:
            logger.bind(tag=TAG).warning("[MEM0-QUERY] Query skipped - use_mem0 is False")
            return ""
        try:
            logger.bind(tag=TAG).info(f"[MEM0-QUERY] Searching memories for user_id: {self.role_id}")
            results = self.client.search(
                query, user_id=self.role_id, output_format=self.api_version
            )
            
            # logger.bind(tag=TAG).info(f"[MEM0-QUERY] Search completed. Results: {results}")
            
            if not results or "results" not in results:
                logger.bind(tag=TAG).info("[MEM0-QUERY] No results found or invalid response format")
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
            logger.bind(tag=TAG).info(f"[MEM0-QUERY] Found {len(memories)} memories")
            logger.bind(tag=TAG).debug(f"[MEM0-QUERY] Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"[MEM0-QUERY] Failed to query memory: {str(e)}")
            logger.bind(tag=TAG).error(f"[MEM0-QUERY] Exception traceback: {traceback.format_exc()}")
            return ""
    
    async def test_mem0_connection(self):
        """Test MEM0 connection and verify saving/retrieval works"""
        logger.bind(tag=TAG).info("[MEM0-TEST] Testing MEM0 connection and functionality")
        
        if not self.use_mem0:
            logger.bind(tag=TAG).error("[MEM0-TEST] MEM0 is disabled (use_mem0=False)")
            return False
        
        try:
            # Test saving a simple message
            test_msg = f"Test message at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            logger.bind(tag=TAG).info(f"[MEM0-TEST] Saving test message: {test_msg}")
            
            test_result = self.client.add(
                test_msg, 
                user_id=self.role_id, 
                output_format=self.api_version
            )
            logger.bind(tag=TAG).info(f"[MEM0-TEST] Test save result: {test_result}")
            
            # Try to retrieve it immediately
            await asyncio.sleep(2)  # Give MEM0 2 seconds to process
            
            logger.bind(tag=TAG).info("[MEM0-TEST] Retrieving test message")
            search_result = self.client.search(
                "test message", 
                user_id=self.role_id, 
                output_format=self.api_version
            )
            logger.bind(tag=TAG).info(f"[MEM0-TEST] Test search result: {search_result}")
            
            return True
        except Exception as e:
            logger.bind(tag=TAG).error(f"[MEM0-TEST] Test failed: {str(e)}")
            return False
