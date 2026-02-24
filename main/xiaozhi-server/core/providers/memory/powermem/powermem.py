#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@time: 2026/01/08
@file: powermem.py
@desc: PowerMem memory provider for xiaozhi-esp32-server
       PowerMem is an open-source agent memory component from OceanBase
       GitHub: https://github.com/oceanbase/powermem
       Website: https://www.powermem.ai/
@Author: wayyoungboy
"""

import asyncio
import json
import traceback
from typing import Optional, Dict, Any

from ..base import MemoryProviderBase, logger

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    """
    PowerMem memory provider implementation.

    PowerMem is an open-source agent memory component that provides
    efficient memory management for AI agents.

    Supports multiple storage backends (sqlite, oceanbase, postgres),
    LLM providers (qwen, openai, etc.) and embedding providers.

    Config options:
        - enable_user_profile: bool - Enable UserMemory for user profiling (requires OceanBase)
        - database_provider: str - Storage backend (sqlite, oceanbase, postgres)
        - llm_provider: str - LLM provider (qwen, openai, etc.)
        - embedding_provider: str - Embedding provider (qwen, openai, etc.)
    """

    def __init__(self, config: Dict[str, Any], summary_memory: Optional[str] = None):
        super().__init__(config)
        self.use_powermem = False
        self.memory_client = None
        self.enable_user_profile = False
        self.last_profile_content = ""  # Cache for user profile from UserMemory

        try:
            # Check if user profile mode is enabled
            self.enable_user_profile = config.get("enable_user_profile", False)
            
            # Get configuration parameters
            database_provider = config.get("database_provider", "sqlite")
            llm_provider = config.get("llm_provider", "qwen")
            embedding_provider = config.get("embedding_provider", "qwen")

            # Build powermem configuration dict
            # PowerMem supports two config styles:
            # 1. powermem style: database, llm, embedding
            # 2. mem0 style: vector_store, llm, embedder
            powermem_config = {}

            # Configure vector store / database
            if "vector_store" in config:
                powermem_config["vector_store"] = config["vector_store"]
            elif "database" in config:
                powermem_config["database"] = config["database"]
            else:
                powermem_config["vector_store"] = {
                    "provider": database_provider,
                    "config": {}
                }

            # Configure LLM
            if "llm" in config:
                powermem_config["llm"] = config["llm"]
            else:
                llm_config = {}
                if "llm_api_key" in config:
                    llm_config["api_key"] = config["llm_api_key"]
                if "llm_model" in config:
                    llm_config["model"] = config["llm_model"]
                # Handle base_url based on provider type
                # - qwen provider uses dashscope_base_url
                # - openai provider uses openai_base_url
                if "llm_base_url" in config:
                    if llm_provider == "qwen":
                        llm_config["dashscope_base_url"] = config["llm_base_url"]
                    else:
                        llm_config["openai_base_url"] = config["llm_base_url"]
                if "openai_base_url" in config:
                    llm_config["openai_base_url"] = config["openai_base_url"]
                if "dashscope_base_url" in config:
                    llm_config["dashscope_base_url"] = config["dashscope_base_url"]
                powermem_config["llm"] = {
                    "provider": llm_provider,
                    "config": llm_config
                }

            # Configure embedder
            if "embedder" in config:
                powermem_config["embedder"] = config["embedder"]
            else:
                embedder_config = {}
                if "embedding_api_key" in config:
                    embedder_config["api_key"] = config["embedding_api_key"]
                if "embedding_model" in config:
                    embedder_config["model"] = config["embedding_model"]
                # Handle base_url based on provider type
                # - qwen provider uses dashscope_base_url
                # - openai provider uses openai_base_url
                # Priority: embedding_xxx_base_url > embedding_base_url > xxx_base_url
                if "embedding_base_url" in config:
                    if embedding_provider == "qwen":
                        embedder_config["dashscope_base_url"] = config["embedding_base_url"]
                    else:
                        embedder_config["openai_base_url"] = config["embedding_base_url"]
                # Embedding-specific base_url (higher priority)
                if "embedding_openai_base_url" in config:
                    embedder_config["openai_base_url"] = config["embedding_openai_base_url"]
                if "embedding_dashscope_base_url" in config:
                    embedder_config["dashscope_base_url"] = config["embedding_dashscope_base_url"]
                powermem_config["embedder"] = {
                    "provider": embedding_provider,
                    "config": embedder_config
                }

            # Initialize memory client based on mode
            if self.enable_user_profile:
                from powermem import UserMemory
                self.memory_client = UserMemory(config=powermem_config)
                memory_mode = "UserMemory (用户画像模式)"
            else:
                from powermem import AsyncMemory
                self.memory_client = AsyncMemory(config=powermem_config)
                memory_mode = "AsyncMemory (普通记忆模式)"

            self.use_powermem = True

            logger.bind(tag=TAG).info(
                f"PowerMem initialized successfully: mode={memory_mode}, "
                f"database={powermem_config['vector_store']['provider']}, llm={powermem_config['llm']['provider']}, embedding={powermem_config['embedder']['provider']}"
            )            
            
        except ImportError as e:
            logger.bind(tag=TAG).error(
                f"PowerMem not installed. Please install with: pip install powermem. Error: {e}"
            )
            self.use_powermem = False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize PowerMem: {str(e)}")
            logger.bind(tag=TAG).debug(f"Detailed error: {traceback.format_exc()}")
            self.use_powermem = False

    async def save_memory(self, msgs, session_id=None):
        """
        Save conversation messages to PowerMem.

        Args:
            msgs: List of message objects with 'role' and 'content' attributes

            session_id: Session identifier (optional, for compatibility)

        Returns:
            Result from PowerMem API or None if failed
        """
        if not self.use_powermem or self.memory_client is None:
            logger.bind(tag=TAG).warning("PowerMem is not available, skipping save_memory")
            return None

        if len(msgs) < 2:
            logger.bind(tag=TAG).debug("Not enough messages to save (need at least 2)")
            return None

        try:
            # Format the content as a message list for PowerMem
            messages = []
            for message in msgs:
                if message.role == "system":
                    continue

                content = message.content

                # Extract content from JSON format if present (for ASR with emotion/language tags)
                # Same logic as in query_memory method
                try:
                    if content and content.strip().startswith("{") and content.strip().endswith("}"):
                        data = json.loads(content)
                        if "content" in data:
                            content = data["content"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    # If parsing fails, use original content
                    pass

                messages.append({"role": message.role, "content": content})

            # Add memory using PowerMem SDK
            result = self.memory_client.add(
                messages=messages,
                user_id=self.role_id
            )
            # Handle both sync and async returns
            if asyncio.iscoroutine(result):
                result = await result

            logger.bind(tag=TAG).debug(f"Save memory result: {result}")

            # Cache user profile if UserMemory mode and profile was extracted
            if self.enable_user_profile and result:
                if result.get('profile_extracted'):
                    self.last_profile_content = result.get('profile_content', '')
                    logger.bind(tag=TAG).debug(f"User profile extracted: {self.last_profile_content}")

            return result

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error saving memory: {str(e)}")
            logger.bind(tag=TAG).debug(f"Detailed error: {traceback.format_exc()}")
            return None

    async def query_memory(self, query: str) -> str:
        """
        Query memories from PowerMem based on similarity search.

        Args:
            query: The search query string (may be JSON format with metadata)

        Returns:
            Formatted string of relevant memories or empty string if none found
        """
        if not self.use_powermem or self.memory_client is None:
            logger.bind(tag=TAG).warning("PowerMem is not available, skipping query_memory")
            return ""

        try:
            if not getattr(self, "role_id", None):
                logger.bind(tag=TAG).debug("No role_id set, returning empty memory")
                return ""

            # Extract content from JSON format if present (for ASR with emotion/language tags)
            search_query = query
            try:
                if query.strip().startswith("{") and query.strip().endswith("}"):
                    data = json.loads(query)
                    if "content" in data:
                        search_query = data["content"]
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, use original query
                pass

            result_parts = []

            # If user profile mode is enabled, include user profile in results
            if self.enable_user_profile:
                profile = await self.get_user_profile()
                if profile:
                    result_parts.append(f"【用户画像】\n{profile}")

            # Search memories using PowerMem SDK
            if self.enable_user_profile:
                # UserMemory uses sync search
                results = await asyncio.to_thread(
                    self.memory_client.search,
                    query=search_query,
                    user_id=self.role_id,
                    limit=30
                )
            else:
                # AsyncMemory uses async search
                results = await self.memory_client.search(
                    query=search_query,
                    user_id=self.role_id,
                    limit=30
                )

            if results and "results" in results:
                # Format each memory entry with its update time
                memories = []
                for entry in results.get("results", []):
                    # Get timestamp from updated_at or created_at
                    timestamp = ""
                    if "updated_at" in entry and entry["updated_at"]:
                        timestamp = str(entry["updated_at"])
                    elif "created_at" in entry and entry["created_at"]:
                        timestamp = str(entry["created_at"])

                    if timestamp:
                        try:
                            # Parse and reformat the timestamp (remove milliseconds if present)
                            if "." in timestamp:
                                dt = timestamp.split(".")[0]
                            else:
                                dt = timestamp
                            formatted_time = dt.replace("T", " ")
                        except Exception:
                            formatted_time = timestamp
                    else:
                        formatted_time = ""

                    memory = entry.get("memory", "") or entry.get("content", "")
                    if memory:
                        if formatted_time:
                            # Store tuple of (timestamp, formatted_string) for sorting
                            memories.append((timestamp, f"[{formatted_time}] {memory}"))
                        else:
                            memories.append(("", memory))

                # Sort by timestamp in descending order (newest first)
                memories.sort(key=lambda x: x[0], reverse=True)

                # Extract only the formatted strings
                if memories:
                    memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
                    result_parts.append(f"【相关记忆】\n{memories_str}")

            final_result = "\n\n".join(result_parts)
            logger.bind(tag=TAG).debug(f"Query results: {final_result}")
            return final_result

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error querying memory: {str(e)}")
            logger.bind(tag=TAG).debug(f"Detailed error: {traceback.format_exc()}")
            return ""

    async def get_user_profile(self) -> str:
        """
        Get user profile from PowerMem (only available in UserMemory mode).
        
        In PowerMem 0.3.0+, user profile is automatically extracted during add()
        and cached in last_profile_content.

        Returns:
            Formatted user profile string or empty string if not available
        """
        if not self.use_powermem or self.memory_client is None:
            return ""

        if not self.enable_user_profile:
            logger.bind(tag=TAG).debug("User profile mode is not enabled")
            return ""

        # Return cached profile content from last add() operation
        if self.last_profile_content:
            return self.last_profile_content

        return ""

