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
            self.enable_user_profile = str(config.get("enable_user_profile", False)).lower() == 'true'
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
                if config.get("llm_api_key"):
                    llm_config["api_key"] = config["llm_api_key"]
                if config.get("llm_model"):
                    llm_config["model"] = config["llm_model"]
                # Handle base_url based on provider type
                # - qwen provider uses dashscope_base_url
                # - openai provider uses openai_base_url
                if llm_provider == "qwen":
                    base_url = config.get("dashscope_base_url") or config.get("llm_base_url")
                    if base_url:
                        llm_config["dashscope_base_url"] = base_url
                else:
                    base_url = config.get("openai_base_url") or config.get("llm_base_url")
                    if base_url:
                        llm_config["openai_base_url"] = base_url

                powermem_config["llm"] = {
                    "provider": llm_provider,
                    "config": llm_config
                }

            # Configure embedder
            if "embedder" in config:
                powermem_config["embedder"] = config["embedder"]
            else:
                embedder_config = {}
                if config.get("embedding_api_key"):
                    embedder_config["api_key"] = config["embedding_api_key"]
                if config.get("embedding_model"):
                    embedder_config["model"] = config["embedding_model"]
                # Handle base_url based on provider type
                # - qwen provider uses dashscope_base_url
                # - openai provider uses openai_base_url
                # Priority: embedding_xxx_base_url > embedding_base_url > xxx_base_url
                if embedding_provider == "qwen":
                    base_url = config.get("embedding_dashscope_base_url") or config.get("embedding_base_url")
                    if base_url:
                        embedder_config["dashscope_base_url"] = base_url
                else:
                    base_url = config.get("embedding_openai_base_url") or config.get("embedding_base_url")
                    if base_url:
                        embedder_config["openai_base_url"] = base_url

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
        try:
            if self.use_powermem and self.memory_client is not None and len(msgs) >= 2:
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
                if self.enable_user_profile:
                    # UserMemory uses sync add
                    result = await asyncio.to_thread(
                        self.memory_client.add,
                        messages=messages,
                        user_id=self.role_id
                    )
                else:
                    # AsyncMemory uses async add
                    result = await self.memory_client.add(
                        messages=messages,
                        user_id=self.role_id
                    )

                logger.bind(tag=TAG).debug(f"Save memory result: {result}")

                # Cache user profile if UserMemory mode and profile was extracted
                if self.enable_user_profile and result:
                    if result.get('profile_extracted'):
                        self.last_profile_content = result.get('profile_content', '')
                        logger.bind(tag=TAG).debug(f"User profile extracted: {self.last_profile_content}")
            else:
                if not self.use_powermem or self.memory_client is None:
                    logger.bind(tag=TAG).warning("PowerMem is not available, skipping save_memory")
                elif len(msgs) < 2:
                    logger.bind(tag=TAG).debug("Not enough messages to save (need at least 2)")
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

        Uses a cache-first strategy:
        1. Check if last_profile_content is already cached
        2. If cached, return immediately (performance optimization)
        3. If cache is empty, fetch from PowerMem SDK
        4. Store fetched profile in cache for next query

        Returns:
            Formatted user profile string or empty string if not available
        """
        if not self.use_powermem or self.memory_client is None:
            return ""

        if not self.enable_user_profile:
            logger.bind(tag=TAG).debug("User profile mode is not enabled")
            return ""

        # Return cached profile content if available (fast path)
        if self.last_profile_content:
            logger.bind(tag=TAG).debug("Returning cached user profile")
            return self.last_profile_content

        # Cache is empty, fetch from PowerMem SDK
        logger.bind(tag=TAG).info("Cache miss, fetching user profile from PowerMem SDK")
        try:
            # Call UserMemory.profile() to get profile data
            profile_data = await asyncio.to_thread(
                self.memory_client.profile,
                self.role_id
            )

            if not profile_data:
                logger.bind(tag=TAG).warning("PowerMem SDK returned empty profile data")
                return ""

            # Try to use profile_content first
            profile_content = profile_data.get("profile_content")
            if profile_content:
                # Update cache with fetched profile_content
                self.last_profile_content = profile_content
                logger.bind(tag=TAG).info(f"Successfully fetched and cached user profile from profile_content (length: {len(self.last_profile_content)})")
                return self.last_profile_content

            # If profile_content is empty, fallback to topics
            topics = profile_data.get("topics")
            if topics:
                import json
                # Serialize topics dict to JSON string for structured profile
                self.last_profile_content = json.dumps(topics, ensure_ascii=False, indent=2)
                logger.bind(tag=TAG).info(f"Successfully fetched and cached user profile from topics (length: {len(self.last_profile_content)})")
                return self.last_profile_content

            # Both profile_content and topics are empty
            logger.bind(tag=TAG).warning("PowerMem SDK returned profile with empty profile_content and topics")
            return ""

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to fetch user profile from SDK: {str(e)}")
            logger.bind(tag=TAG).debug(f"Detailed error: {traceback.format_exc()}")
            return ""

