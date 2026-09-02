from ..base import MemoryProviderBase, logger
import time
import json
import os
import yaml
from config.config_loader import get_project_dir
from config.manage_api_client import generate_and_save_chat_summary
import asyncio
from core.utils.util import check_model_key


short_term_memory_prompt = """
# Time-Space Memory Weaver

## Core Mission
Construct a growable dynamic memory network that retains key information within limited space while intelligently maintaining the trajectory of information evolution.
Summarize important user information from dialogue records to provide more personalized services in future conversations.

## Memory Laws
### 1. Three-Dimensional Memory Assessment (Executed on every update)
| Dimension | Assessment Criteria | Weight |
|---|---|---|
| Timeliness | Information Freshness (by dialogue turns) | 40% |
| Emotional Intensity | Containing 💖 markers/Repetition frequency | 35% |
| Association Density | Number of connections with other information | 25% |

### 2. Dynamic Update Mechanism
**Name Change Handling Example:**
Original Memory: "Former Name": ["John Doe"], "Current Name": "John Smith"
Trigger Condition: When detection signals like "My name is X", "Call me Y" appear
Operation Flow:
1. Move old name to "Former Name" list
2. Record naming timeline: "2024-02-15 14:32: Enable John Smith"
3. Append to Memory Cube: "Identity transformation from John Doe to John Smith"

### 3. Space Optimization Strategy
- **Information Compression**: Use symbol system to increase density
  - ✅"John Smith[North/SE/🐱]"
  - ❌"Beijing Software Engineer, raises a cat"
- **Elimination Warning**: Triggered when total character count ≥ 900
  1. Delete information with weight score < 60 and not mentioned in 3 turns
  2. Merge similar entries (keep the one with latest timestamp)

## Memory Structure
Output format must be a parsable JSON string, no explanation, comments or descriptions needed. Only extract information from dialogue when saving memory, do not mix in example content.
```json
{
  "TimeSpaceArchives": {
    "IdentityGraph": {
      "CurrentName": "",
      "FeatureTags": [] 
    },
    "MemoryCube": [
      {
        "Event": "Joined new company",
        "Timestamp": "2024-03-20",
        "EmotionalValue": 0.9,
        "RelatedItems": ["Afternoon Tea"],
        "ShelfLife": 30 
      }
    ]
  },
  "RelationshipNetwork": {
    "HighFreqTopics": {"Work": 12},
    "HiddenConnections": [""]
  },
  "PendingResponse": {
    "UrgentMatters": ["Tasks needing immediate attention"], 
    "PotentialCare": ["Help that can be proactively offered"]
  },
  "HighlightQuotes": [
    "Most touching moments, strong emotional expressions, user's original words"
  ]
}
```
"""


def extract_json_data(json_code):
    start = json_code.find("```json")
    # Find next ``` end from start
    end = json_code.find("```", start + 1)
    # print("start:", start, "end:", end)
    if start == -1 or end == -1:
        try:
            jsonData = json.loads(json_code)
            return json_code
        except Exception as e:
            print("Error:", e)
        return ""
    jsonData = json_code[start + 7 : end]
    return jsonData


TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory):
        super().__init__(config)
        self.short_memory = ""
        self.save_to_file = True
        self.memory_path = get_project_dir() + "data/.memory.yaml"
        self.load_memory(summary_memory)

    def init_memory(
        self, role_id, llm, summary_memory=None, save_to_file=True, **kwargs
    ):
        super().init_memory(role_id, llm, **kwargs)
        self.save_to_file = save_to_file
        self.load_memory(summary_memory)

    def load_memory(self, summary_memory):
        # Return directly after API gets summary memory
        if summary_memory or not self.save_to_file:
            self.short_memory = summary_memory
            return

        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = yaml.safe_load(f) or {}
        if self.role_id in all_memory:
            self.short_memory = all_memory[self.role_id]

    def save_memory_to_file(self):
        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = yaml.safe_load(f) or {}
        all_memory[self.role_id] = self.short_memory
        with open(self.memory_path, "w", encoding="utf-8") as f:
            yaml.dump(all_memory, f, allow_unicode=True)

    async def save_memory(self, msgs, session_id=None):
        # Print model info used
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"Using memory save model: {model_info}")
        api_key = getattr(self.llm, "api_key", None)
        memory_key_msg = check_model_key("Memory Summary LLM", api_key)
        if memory_key_msg:
            logger.bind(tag=TAG).error(memory_key_msg)
        if self.llm is None:
            logger.bind(tag=TAG).error("LLM is not set for memory provider")
            return None

        if len(msgs) < 2:
            return None

        msgStr = ""
        for msg in msgs:
            if msg.role == "user":
                msgStr += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                msgStr += f"Assistant: {msg.content}\n"
        if self.short_memory and len(self.short_memory) > 0:
            msgStr += "History Memory:\n"
            msgStr += self.short_memory

        # Current Time
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        msgStr += f"Current Time: {time_str}"

        if self.save_to_file:
            result = self.llm.response_no_stream(
                short_term_memory_prompt,
                msgStr,
                max_tokens=2000,
                temperature=0.2,
            )
            json_str = extract_json_data(result)
            try:
                json.loads(json_str)  # Check if json format is correct
                self.short_memory = json_str
                self.save_memory_to_file()
            except Exception as e:
                print("Error:", e)
        else:
            # When save_to_file is False, call chat record summary interface on Java side
            summary_id = session_id if session_id else self.role_id
            await generate_and_save_chat_summary(summary_id)
        logger.bind(tag=TAG).info(
            f"Save memory successful - Role: {self.role_id}, Session: {session_id}"
        )

        return self.short_memory

    async def query_memory(self, query: str) -> str:
        return self.short_memory
