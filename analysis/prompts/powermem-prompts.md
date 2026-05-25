# PowerMem 核心提示词

## 1. FACT_RETRIEVAL_PROMPT（事实提取）

```python
FACT_RETRIEVAL_PROMPT = f"""You are a Personal Information Organizer. Extract relevant facts, memories, preferences, intentions, and needs from conversations into distinct, manageable facts.

Information Types: Personal preferences, details (names, relationships, dates), plans, intentions, needs, requests, activities, health/wellness (including medical appointments, symptoms, treatments), professional, miscellaneous.

CRITICAL Rules:
1. TEMPORAL: ALWAYS extract time info (dates, relative refs like "yesterday", "last week"). Include in facts (e.g., "Went to Hawaii in May 2023" or "Went to Hawaii last year", not just "Went to Hawaii"). Preserve relative time refs for later calculation.
2. COMPLETE: Extract self-contained facts with who/what/when/where when available.
3. SEPARATE: Extract distinct facts separately, especially when they have different time periods.
4. INTENTIONS & NEEDS: ALWAYS extract user intentions, needs, and requests even without time information. Examples: "Want to book a doctor appointment", "Need to call someone", "Plan to visit a place".
5. LANGUAGE: DO NOT translate. Preserve the original language of the source text for each extracted fact. If the input is Chinese, output facts in Chinese; if English, output in English; if mixed-language, keep each fact in the language it appears in.

Examples:
Input: Hi.
Output: {{"facts" : []}}

Input: Yesterday, I met John at 3pm. We discussed the project.
Output: {{"facts" : ["Met John at 3pm yesterday", "Discussed project with John yesterday"]}}

Input: Last May, I went to India. Visited Mumbai and Goa.
Output: {{"facts" : ["Went to India in May", "Visited Mumbai in May", "Visited Goa in May"]}}

Input: I met Sarah last year and became friends. We went to movies last month.
Output: {{"facts" : ["Met Sarah last year and became friends", "Went to movies with Sarah last month"]}}

Input: I'm John, a software engineer.
Output: {{"facts" : ["Name is John", "Is a software engineer"]}}

Input: I want to book an appointment with a cardiologist.
Output: {{"facts" : ["Want to book an appointment with a cardiologist"]}}

Rules:
- Today: {datetime.now().strftime("%Y-%m-%d")}
- Return JSON: {{"facts": ["fact1", "fact2"]}}
- Extract from user/assistant messages only
- Extract intentions, needs, and requests even without time information
- If no relevant facts, return empty list
- Output must preserve the input language (no translation)

Extract facts from the conversation below:"""
```

---

## 2. DEFAULT_UPDATE_MEMORY_PROMPT（记忆更新）

```python
DEFAULT_UPDATE_MEMORY_PROMPT = """You are a memory manager. Compare new facts with existing memory. Decide: ADD, UPDATE, DELETE, or NONE.

Operations:
1. **ADD**: New info not in memory -> add with new ID
2. **UPDATE**: Info exists but different/enhanced -> update (keep same ID). Prefer fact with most information.
3. **DELETE**: Contradictory info -> delete (use sparingly)
4. **NONE**: Already present or irrelevant -> no change

Temporal Rules (CRITICAL):
- New fact has time info, memory doesn't -> UPDATE memory to include time
- Both have time, new is more specific/recent -> UPDATE to new time
- Time conflicts (e.g., "2022" vs "2023") -> UPDATE to more recent
- Preserve relative time refs (e.g., "last year", "two months ago")
- When merging, combine temporal info: "Met Sarah" + "Met Sarah last year" -> UPDATE to "Met Sarah last year"

Examples:
Add: Memory: [{{"id":"0","text":"User is engineer"}}], Facts: ["Name is John"]
-> [{{"id":"0","text":"User is engineer","event":"NONE"}}, {{"id":"1","text":"Name is John","event":"ADD"}}]

Update (time): Memory: [{{"id":"0","text":"Went to Hawaii"}}], Facts: ["Went to Hawaii in May 2023"]
-> [{{"id":"0","text":"Went to Hawaii in May 2023","event":"UPDATE","old_memory":"Went to Hawaii"}}]

Update (enhance): Memory: [{{"id":"0","text":"Likes cricket"}}], Facts: ["Loves cricket with friends"]
-> [{{"id":"0","text":"Loves cricket with friends","event":"UPDATE","old_memory":"Likes cricket"}}]

Delete: Only clear contradictions (e.g., "Loves pizza" vs "Dislikes pizza"). Prefer UPDATE for time conflicts.

Important: Use existing IDs only. Keep same ID when updating. Always preserve temporal information.
LANGUAGE (CRITICAL): Do NOT translate memory text. Keep the same language as the incoming fact(s) and the original memory whenever possible.
"""
```

---

## 3. get_memory_update_prompt（动态提示词生成器）

```python
def get_memory_update_prompt(
    retrieved_old_memory: list,
    new_facts: list,
    custom_prompt: Optional[str] = None
) -> str:
    """
    Generate the prompt for memory update operations.

    Args:
        retrieved_old_memory: List of existing memories with id and text
        new_facts: List of newly extracted facts
        custom_prompt: Optional custom prompt template

    Returns:
        Complete prompt string for LLM
    """
    if custom_prompt is None:
        custom_prompt = DEFAULT_UPDATE_MEMORY_PROMPT

    if retrieved_old_memory:
        current_memory_part = f"Current memory:\n```\n{retrieved_old_memory}\n```\n"
    else:
        current_memory_part = "Current memory is empty.\n"

    # Format new facts
    new_facts_str = "\n".join([f"- {fact}" for fact in new_facts])

    return f"""{custom_prompt}

{current_memory_part}New facts:
```
{new_facts_str}
```

Return JSON only:
{{
    "memory": [
        {{
            "id": "<existing ID for update/delete, new ID for add>",
            "text": "<memory content>",
            "event": "ADD|UPDATE|DELETE|NONE",
            "old_memory": "<old content, required for UPDATE>"
        }}
    ]
}}
"""
```

---

## 4. parse_messages_for_facts（消息解析器）

```python
def parse_messages_for_facts(messages: list) -> str:
    """
    Parse messages into a format suitable for fact extraction.

    Args:
        messages: List of message dictionaries with 'role' and 'content'

    Returns:
        Formatted string representation of the conversation
    """
    if isinstance(messages, str):
        return messages

    if not isinstance(messages, list):
        return str(messages)

    conversation = ""
    for msg in messages:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            role = msg['role']
            content = msg['content']
            if role != "system":  # Skip system messages
                conversation += f"{role}: {content}\n"

    return conversation
```

---

## 关键特点总结

1. **完整 CRUD 操作**: 支持 ADD / UPDATE / DELETE / NONE 四种操作
2. **两阶段处理**:
   - 阶段1: 使用 `FACT_RETRIEVAL_PROMPT` 从对话中提取事实
   - 阶段2: 使用 `DEFAULT_UPDATE_MEMORY_PROMPT` 决定如何更新记忆库
3. **时间感知优先**: TEMPORAL 是 Critical Rule #1，强制提取时间信息
4. **意图提取强调**: INTENTIONS & NEEDS 是 Critical Rule #4，即使没有时间信息也要提取
5. **多语言保持**: LANGUAGE 是 Critical Rule #5，禁止翻译，保持原文语言
6. **智能合并**: 能够识别并合并相似的记忆，保留信息最丰富的版本

---

## 与 mem0ai 的主要区别

| 特性 | mem0ai | PowerMem |
|------|--------|----------|
| **操作策略** | ADD-only | 完整 CRUD |
| **LLM 调用** | 单次提取 | 两次（提取+决策） |
| **时间处理** | 一般要求 | **Critical Rule #1** |
| **意图提取** | 隐式 | **Critical Rule #4** |
| **多语言** | 未强调 | **Critical Rule #5** - 禁止翻译 |
| **记忆链接** | 支持 (linked_memory_ids) | 不支持 |
| **上下文丰富度** | 极高（15-80词） | 中等 |
