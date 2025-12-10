#!/usr/bin/env python
# coding=utf-8
# Copyright 2025 The OPPO Personal AI team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import argparse
import os
import yaml
import torch
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
from memory_chain import MemoryChain, MemoryManager


# ==================== Configuration Class ====================

class MemoryConfig:
    """Memory system configuration"""
    def __init__(
        self,
        working_memory_max_size: int = 20,
        episodic_memory_refresh_rate: int = 5,
        output_dir: str = "./memory_storage",
        number_of_retrieval_pieces: int = 15,  # Must be >= 10 (internal calculation uses top_k-9)
        drop_threshold: float = 0.1,
    ):
        self.working_memory_max_size = working_memory_max_size
        self.episodic_memory_refresh_rate = episodic_memory_refresh_rate
        self.output_dir = output_dir
        self.number_of_retrieval_pieces = max(number_of_retrieval_pieces, 10)  # Ensure at least 10
        self.drop_threshold = drop_threshold


# ==================== Main Usage Example ====================

async def main():
    """
    Memory Chain Usage Example
    """
    
    # ========== 1. Configuration Parameters ==========
    
    # Read config file (or set directly)
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        # If no config file, use default configuration
        config = {
            "model": {
                "llm_model": "gpt-4o-mini",
                "openai_api_key": "your-api-key-here",
                "openai_base_url": "https://api.openai.com/v1"
            }
        }
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        base_url=config["model"]["openai_base_url"],
        api_key=config["model"]["openai_api_key"]
    )
    
    # Load Embedding model
    print("Loading Embedding model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2").to(device)
    print(f"Embedding model loaded, using device: {device}")
    
    # Memory system configuration
    # Note: working_memory_max_size determines the working memory capacity
    # When message count reaches this value, old messages are transferred to episodic memory
    memory_config = MemoryConfig(
        working_memory_max_size=5,       # Max working memory capacity (small value to trigger memory transfer quickly)
        episodic_memory_refresh_rate=3,  # Episodic memory refresh rate
        output_dir="./memory_storage",   # Memory storage directory
        number_of_retrieval_pieces=15,   # Number of retrieval pieces
        drop_threshold=0.1               # Similarity threshold
    )
    
    # Ensure storage directory exists
    os.makedirs(memory_config.output_dir, exist_ok=True)
    
    # ========== 2. Initialize Memory System ==========
    
    user_name = "Alice"    # User name
    agent_name = "Bob"     # Agent/assistant name
    memory_index = 0       # Memory index (for multi-session scenarios)
    
    # Create MemoryChain (core memory system)
    memory_system = MemoryChain(
        memory_index=memory_index,
        llm_model=config["model"]["llm_model"],
        llm_client=client,
        embedding_model=embedding_model,
        user_name=user_name,
        agent_name=agent_name,
        cmd_args=memory_config,
        args=config,
        memory_dir=memory_config.output_dir
    )
    
    # Create MemoryManager (memory manager, provides high-level API)
    memory_manager = MemoryManager(
        memory_index=memory_index,
        memory_system=memory_system,
        llm_model=config["model"]["llm_model"],
        llm_client=client,
        embedding_model=embedding_model,
        user_name=user_name,
        agent_name=agent_name,
        cmd_args=memory_config,
        args=config,
        memory_dir=memory_config.output_dir
    )
    
    print(f"\n{'='*50}")
    print("Memory system initialization complete!")
    print(f"User: {user_name}, Agent: {agent_name}")
    print(f"{'='*50}\n")
    
    # ========== 3. Simulate Conversation and Store Memory ==========
    
    # Simulated conversation data
    # Note: Number of conversations must exceed working_memory_max_size to trigger memory transfer
    conversations = [
        {"speaker": user_name, "message": "I love playing basketball with my friends every weekend.", "timestamp": "2024-01-01 10:00:00"},
        {"speaker": agent_name, "message": "That sounds great! Basketball is a wonderful way to stay active.", "timestamp": "2024-01-01 10:01:00"},
        {"speaker": user_name, "message": "Yes! I've been playing for 5 years. My favorite team is the Lakers.", "timestamp": "2024-01-01 10:02:00"},
        {"speaker": agent_name, "message": "The Lakers have a great history. Do you play any position specifically?", "timestamp": "2024-01-01 10:03:00"},
        {"speaker": user_name, "message": "I usually play as a point guard. I also started learning guitar last month.", "timestamp": "2024-01-01 10:04:00"},
        {"speaker": agent_name, "message": "Guitar is a lovely instrument! What kind of music do you want to play?", "timestamp": "2024-01-01 10:05:00"},
        {"speaker": user_name, "message": "I'm into rock music. My favorite band is Coldplay.", "timestamp": "2024-01-01 10:06:00"},
        {"speaker": agent_name, "message": "Coldplay has some amazing songs. Do you have a favorite album?", "timestamp": "2024-01-01 10:07:00"},
        {"speaker": user_name, "message": "I really love 'A Rush of Blood to the Head'. The song 'The Scientist' is my favorite.", "timestamp": "2024-01-01 10:08:00"},
        {"speaker": agent_name, "message": "That's a classic! Do you also enjoy attending live concerts?", "timestamp": "2024-01-01 10:09:00"},
        {"speaker": user_name, "message": "Yes! I went to a Coldplay concert last year. It was an amazing experience.", "timestamp": "2024-01-01 10:10:00"},
        {"speaker": agent_name, "message": "That must have been incredible! Live music is always so energizing.", "timestamp": "2024-01-01 10:11:00"},
        {"speaker": user_name, "message": "Absolutely! I also enjoy cooking Italian food on weekends.", "timestamp": "2024-01-01 10:12:00"},
        {"speaker": agent_name, "message": "Italian cuisine is delicious! What's your specialty dish?", "timestamp": "2024-01-01 10:13:00"},
        {"speaker": user_name, "message": "I make a great homemade pasta with tomato sauce. My family loves it.", "timestamp": "2024-01-01 10:14:00"},
        {"speaker": agent_name, "message": "That sounds delicious! Cooking for family is always special.", "timestamp": "2024-01-01 10:15:00"},
    ]
    
    print("Processing conversations and building memory...")
    print("-" * 50)
    
    for index, conv in enumerate(conversations):
        speaker = conv["speaker"]
        message = conv["message"]
        timestamp = conv["timestamp"]
        user_speak = (speaker == user_name)
        
        print(f"[{index}] {speaker}: {message}")
        
        # Store message in memory system
        await memory_manager.receive_message(
            message=message,
            client=client,
            index=index,
            timestamp=timestamp,
            user_speak=user_speak
        )
    
    print("-" * 50)
    print("Conversation processing complete!\n")
    
    # ========== 4. Sync Memory Mappings (Important! Must be called before retrieval) ==========
    
    print("Syncing memory mappings...")
    # Sync messages from working_memory and episodic_memory to topic_message_dict
    for message in list(memory_system.user_working_memory.working_memory_queue.queue) + memory_system.user_episodic_memory.episodic_memory_cache_list:
        memory_system.user_topic_message_dict[message["topics"]] = [message["raw_message"], message["timestamp"]]
    for message in list(memory_system.agent_working_memory.working_memory_queue.queue) + memory_system.agent_episodic_memory.episodic_memory_cache_list:
        memory_system.agent_topic_message_dict[message["topics"]] = [message["raw_message"], message["timestamp"]]
    
    # Generate memory detail map (for keyword retrieval)
    memory_system.generate_memory_detail_map()
    print("Memory mapping sync complete!\n")
    
    # ========== 5. Update Persona Memory (Optional, call after conversation ends) ==========
    
    print("Updating persona memory...")
    await memory_system.user_persona_memory.update_preference_persona(
        memory_system.user_episodic_memory.topic_episodic_memory_list
    )
    await memory_system.user_persona_memory.update_attribute_persona(
        memory_system.user_episodic_memory.attribute_episodic_memory_dict
    )
    print("Persona memory update complete!\n")
    
    # ========== 6. Memory Retrieval ==========
    
    print("=" * 50)
    print("Memory Retrieval Example")
    print("=" * 50)
    
    # Test questions
    test_questions = [
        f"What sport does {user_name} like?",
        f"What instrument is {user_name} learning?",
        f"What is {user_name}'s favorite band?",
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)
        
        # Retrieve relevant information from memory system
        retrieval_result, retrieved_user, retrieved_agent, peak_mem, peak_mem_inc = \
            memory_manager.retrieve_from_memory_soft_segmentation(
                question=question,
                topn=memory_config.number_of_retrieval_pieces,
                drop_threshold=memory_config.drop_threshold
            )
        
        # Display retrieval results
        print(f"Retrieved persona attributes: {retrieval_result.get('persona attributes', [])}")
        print(f"Retrieved context messages: {retrieval_result.get('retrieved context messages', [])[:3]}")
        
        # Generate answer
        answer, tokens = await memory_manager.generate_system_response(
            query=question,
            restrieval_result=retrieval_result,
            client=client,
            speaker_a=retrieved_user,
            speaker_b=retrieved_agent,
            llm_model=config["model"]["llm_model"]
        )
        
        print(f"Generated answer: {answer}")
        print(f"Tokens consumed: {tokens}")
    
    print("\n" + "=" * 50)
    print("Example run complete!")
    print("=" * 50)


# ==================== Simplified API Wrapper ====================

class SimpleMemory:
    """
    Simplified memory system wrapper class
    Provides simpler API for everyday use
    """
    
    def __init__(
        self,
        user_name: str,
        agent_name: str,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        memory_dir: str = "./memory_storage",
    ):
        self.user_name = user_name
        self.agent_name = agent_name
        self.llm_model = llm_model
        self.memory_dir = memory_dir
        self.message_index = 0
        
        # Initialize client
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        
        # Load Embedding model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedding_model = SentenceTransformer(embedding_model_name).to(device)
        
        # Configuration
        self.config = {"model": {"llm_model": llm_model}}
        self.cmd_args = MemoryConfig(
            working_memory_max_size=5,       # Same as main() for consistent behavior
            episodic_memory_refresh_rate=3,  # Same as main()
            output_dir=memory_dir
        )
        
        os.makedirs(memory_dir, exist_ok=True)
        
        # Initialize memory system
        self.memory_system = MemoryChain(
            memory_index=0,
            llm_model=llm_model,
            llm_client=self.client,
            embedding_model=self.embedding_model,
            user_name=user_name,
            agent_name=agent_name,
            cmd_args=self.cmd_args,
            args=self.config,
            memory_dir=memory_dir
        )
        
        self.memory_manager = MemoryManager(
            memory_index=0,
            memory_system=self.memory_system,
            llm_model=llm_model,
            llm_client=self.client,
            embedding_model=self.embedding_model,
            user_name=user_name,
            agent_name=agent_name,
            cmd_args=self.cmd_args,
            args=self.config,
            memory_dir=memory_dir
        )
    
    async def add_message(self, message: str, is_user: bool = True, timestamp: str = None):
        """Add a message to memory"""
        from datetime import datetime
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await self.memory_manager.receive_message(
            message=message,
            client=self.client,
            index=self.message_index,
            timestamp=timestamp,
            user_speak=is_user
        )
        self.message_index += 1
    
    async def query(self, question: str) -> str:
        """Query memory and generate answer"""
        # Sync memory mappings
        self._sync_memory_mappings()
        
        result, user, agent, _, _ = self.memory_manager.retrieve_from_memory_soft_segmentation(
            question=question,
            topn=self.cmd_args.number_of_retrieval_pieces,
            drop_threshold=self.cmd_args.drop_threshold
        )
        
        answer, _ = await self.memory_manager.generate_system_response(
            query=question,
            restrieval_result=result,
            client=self.client,
            speaker_a=user,
            speaker_b=agent,
            llm_model=self.llm_model
        )
        return answer
    
    def _sync_memory_mappings(self):
        """Sync memory mappings (must be called before retrieval)"""
        for message in list(self.memory_system.user_working_memory.working_memory_queue.queue) + self.memory_system.user_episodic_memory.episodic_memory_cache_list:
            self.memory_system.user_topic_message_dict[message["topics"]] = [message["raw_message"], message["timestamp"]]
        for message in list(self.memory_system.agent_working_memory.working_memory_queue.queue) + self.memory_system.agent_episodic_memory.episodic_memory_cache_list:
            self.memory_system.agent_topic_message_dict[message["topics"]] = [message["raw_message"], message["timestamp"]]
        self.memory_system.generate_memory_detail_map()
    
    async def update_persona(self):
        """Update persona memory"""
        # Sync memory mappings first
        self._sync_memory_mappings()
        
        await self.memory_system.user_persona_memory.update_preference_persona(
            self.memory_system.user_episodic_memory.topic_episodic_memory_list
        )
        await self.memory_system.user_persona_memory.update_attribute_persona(
            self.memory_system.user_episodic_memory.attribute_episodic_memory_dict
        )


# ==================== Simplified Usage Example ====================

async def simple_example():
    """Simplified API usage example - processes the same conversation as main()"""
    
    print("\n" + "=" * 50)
    print("Simplified API Usage Example")
    print("=" * 50 + "\n")
    
    # Read configuration
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    user_name = "Alice"
    agent_name = "Bob"
    
    # Create simplified memory system
    memory = SimpleMemory(
        user_name=user_name,
        agent_name=agent_name,
        llm_model=config["model"]["llm_model"],
        api_key=config["model"]["openai_api_key"],
        base_url=config["model"]["openai_base_url"],
        memory_dir="./memory_storage_simple",  # Use different storage directory
    )
    
    # Simulated conversation data (same as main())
    conversations = [
        {"speaker": user_name, "message": "I love playing basketball with my friends every weekend.", "timestamp": "2024-01-01 10:00:00"},
        {"speaker": agent_name, "message": "That sounds great! Basketball is a wonderful way to stay active.", "timestamp": "2024-01-01 10:01:00"},
        {"speaker": user_name, "message": "Yes! I've been playing for 5 years. My favorite team is the Lakers.", "timestamp": "2024-01-01 10:02:00"},
        {"speaker": agent_name, "message": "The Lakers have a great history. Do you play any position specifically?", "timestamp": "2024-01-01 10:03:00"},
        {"speaker": user_name, "message": "I usually play as a point guard. I also started learning guitar last month.", "timestamp": "2024-01-01 10:04:00"},
        {"speaker": agent_name, "message": "Guitar is a lovely instrument! What kind of music do you want to play?", "timestamp": "2024-01-01 10:05:00"},
        {"speaker": user_name, "message": "I'm into rock music. My favorite band is Coldplay.", "timestamp": "2024-01-01 10:06:00"},
        {"speaker": agent_name, "message": "Coldplay has some amazing songs. Do you have a favorite album?", "timestamp": "2024-01-01 10:07:00"},
        {"speaker": user_name, "message": "I really love 'A Rush of Blood to the Head'. The song 'The Scientist' is my favorite.", "timestamp": "2024-01-01 10:08:00"},
        {"speaker": agent_name, "message": "That's a classic! Do you also enjoy attending live concerts?", "timestamp": "2024-01-01 10:09:00"},
        {"speaker": user_name, "message": "Yes! I went to a Coldplay concert last year. It was an amazing experience.", "timestamp": "2024-01-01 10:10:00"},
        {"speaker": agent_name, "message": "That must have been incredible! Live music is always so energizing.", "timestamp": "2024-01-01 10:11:00"},
        {"speaker": user_name, "message": "Absolutely! I also enjoy cooking Italian food on weekends.", "timestamp": "2024-01-01 10:12:00"},
        {"speaker": agent_name, "message": "Italian cuisine is delicious! What's your specialty dish?", "timestamp": "2024-01-01 10:13:00"},
        {"speaker": user_name, "message": "I make a great homemade pasta with tomato sauce. My family loves it.", "timestamp": "2024-01-01 10:14:00"},
        {"speaker": agent_name, "message": "That sounds delicious! Cooking for family is always special.", "timestamp": "2024-01-01 10:15:00"},
    ]
    
    # Add all conversations
    print("Processing conversations and building memory...")
    print("-" * 50)
    
    for conv in conversations:
        speaker = conv["speaker"]
        message = conv["message"]
        timestamp = conv["timestamp"]
        is_user = (speaker == user_name)
        
        print(f"{'[User]' if is_user else '[Agent]'} {speaker}: {message[:50]}...")
        await memory.add_message(message, is_user=is_user, timestamp=timestamp)
    
    print("-" * 50)
    print("Conversation processing complete!\n")
    
    # Update persona memory
    print("Updating persona memory...")
    await memory.update_persona()
    print("Persona memory update complete!\n")
    
    # Test questions
    print("=" * 50)
    print("Memory Retrieval Example")
    print("=" * 50)
    
    test_questions = [
        f"What sport does {user_name} like?",
        f"What instrument is {user_name} learning?",
        f"What is {user_name}'s favorite band?",
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)
        answer = await memory.query(question)
        print(f"Answer: {answer}")
    
    print("\n" + "=" * 50)
    print("Simplified example run complete!")
    print("=" * 50)


# ==================== Entry Point ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        # Run simplified example
        print("Running simplified example...")
        asyncio.run(simple_example())
    else:
        # Run full example (default)
        print("Running full example...")
        asyncio.run(main())
    
    # Usage:
    # python example_usage.py          # Run full example
    # python example_usage.py simple   # Run simplified example


