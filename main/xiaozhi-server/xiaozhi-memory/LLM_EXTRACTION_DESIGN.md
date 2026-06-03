# xiaozhi-memory LLM 记忆提取方案

## 设计理念

结合 **mem0ai V3** 和 **PowerMem** 的优点，设计适合小智 ESP32 服务器的 LLM 记忆提取方案。

---

## 核心策略选择

| 特性 | mem0ai V3 | PowerMem | **本方案** |
|------|-----------|----------|-----------|
| **操作策略** | Add-only | 完整 CRUD | **Add-only + 链接** |
| **LLM 调用** | 单次 | 两次（提取+决策） | **单次提取** |
| **时间处理** | Observation Date | Critical Rule #1 | **Critical Rule #1** |
| **意图提取** | 隐式 | Critical Rule #4 | **Critical Rule #4** |
| **多语言** | 未强调 | Critical Rule #5 | **Critical Rule #5** |
| **记忆链接** | ✅ linked_memory_ids | ❌ | **✅ linked_memory_ids** |
| **上下文丰富度** | 15-80词 | 中等 | **15-80词** |

**选择理由**：
- **Add-only**：简单高效，适合嵌入式设备，通过检索算法解决质量问题
- **记忆链接**：建立记忆间关联，提升检索相关性
- **Critical Rules**：保留 PowerMem 的核心规则（时间、意图、多语言）

---

## 提示词设计

### FACT_EXTRACTION_PROMPT

```python
FACT_EXTRACTION_PROMPT = """你是一个个人信息提取助手。从对话中提取相关事实、记忆、偏好和意图。

CRITICAL 规则（按优先级）:
1. TEMPORAL (时间): 始终提取时间信息。将相对时间转换为绝对时间，同时保留原始时间描述
   - 例如: "两天后" → "2025-05-22 (两天后)"
   - 使用 Observation Date 解析相对时间

2. INTENTIONS (意图): 始终提取用户的意图、需求和请求，即使没有时间信息
   - 例如: "我想约个心脏科医生" → 意图记忆
   - "明天要去开会" → 意图记忆

3. LANGUAGE (语言): 不要翻译！保持原文语言
   - 中文输入 → 中文输出
   - 英文输入 → 英文输出
   - 混合输入 → 分别保持

4. COMPLETE (完整): 提取完整的事实，包含谁/什么/何时/何地
   - 15-80词，上下文丰富
   - 包含情感反应、动机

5. SEPARATE (分离): 不同时间段的事实用分开提取
   - 不同主题分别提取

6. ATTRIBUTION (归属): 正确归属信息来源
   - 用户陈述 → "User ..."
   - 助手推荐 → "User was recommended ..."

记忆类型:
- FACT: 已发生的事实（"昨天去了北京"）
- INTENTION: 未来的计划和意图（"明天要去开会"）
- PREFERENCE: 偏好（"喜欢喝咖啡"）

输出格式:
{
  "facts": [
    {
      "content": "记忆内容（保持原文语言，15-80词，上下文丰富）",
      "type": "FACT|INTENTION|PREFERENCE",
      "time_info": {"absolute": "2025-05-22", "relative": "两天后"},
      "intention_type": "meeting|travel|task|purchase|appointment|...",
      "linked_memory_ids": ["uuid1", "uuid2"]
    }
  ]
}

如果提取到与现有记忆相关的新记忆，在 linked_memory_ids 中添加相关记忆的ID。

今天的日期: {current_date}
观察日期（用于解析相对时间）: {observation_date}

最近提取的记忆:
{recently_extracted}

现有记忆:
{existing_memories}

从以下对话中提取信息:
{conversation}

只返回 JSON，不要其他内容。"""
```

---

## 处理流程

```
┌─────────────────────────────────────────────────────────────┐
│                    add_memory(messages, user_id)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 格式化消息                                              │
│     - 过滤 system 消息                                      │
│     - 处理 JSON 格式（ASR 情感标签）                        │
│     - 构建 conversation 字符串                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 获取上下文                                              │
│     - recently_extracted: 本会话最近提取的记忆（20条）      │
│     - existing_memories: 相关的现有记忆（FTS5 检索）         │
│     - current_date: 今天日期                               │
│     - observation_date: 对话发生日期                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. LLM 提取（单次调用）                                    │
│     - 使用 FACT_EXTRACTION_PROMPT                          │
│     - 返回结构化的 facts 列表                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 去重与链接                                              │
│     - 与 recently_extracted 去重                           │
│     - 检查与 existing_memories 的相似性                     │
│     - 建立 linked_memory_ids                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 存储记忆                                                │
│     - 创建 Memory 对象（FactMemory/IntentionMemory）        │
│     - 保存到 SQLite                                        │
│     - FTS5 索引自动更新                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      返回 {"added": n, "updated": 0, "skipped": m}
```

---

## 记忆对象映射

### LLM 输出 → Memory 对象

```python
def llm_output_to_memory(fact: dict, user_id: str) -> BaseMemory:
    """将 LLM 输出转换为 Memory 对象"""
    
    fact_type = fact.get("type", "FACT")
    
    common_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "content": fact["content"],
        "type": MemoryType.FACT if fact_type == "FACT" else MemoryType.INTENTION,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "related_ids": fact.get("linked_memory_ids", []),
        "time_info": fact.get("time_info"),
    }
    
    if fact_type == "INTENTION":
        common_data.update({
            "intention_status": IntentionStatus.PLANNED,
            "planned_time": parse_absolute_time(fact.get("time_info", {}).get("absolute")),
            "time_description": fact.get("time_info", {}).get("relative"),
            "intention_type": fact.get("intention_type"),
        })
        return IntentionMemory(**common_data)
    
    return FactMemory(**common_data)
```

---

## LLM 客户端接口

```python
class LLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    async def extract_facts(
        self,
        conversation: str,
        context: dict
    ) -> List[dict]:
        """提取事实"""
        pass
```

### OpenAI 实现

```python
class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def extract_facts(self, conversation: str, context: dict) -> List[dict]:
        prompt = FACT_EXTRACTION_PROMPT.format(**context, conversation=conversation)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的个人信息提取助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("facts", [])
```

### Ollama 实现（本地免费）

```python
class OllamaClient(LLMClient):
    def __init__(self, model: str = "qwen2:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    async def extract_facts(self, conversation: str, context: dict) -> List[dict]:
        prompt = FACT_EXTRACTION_PROMPT.format(**context, conversation=conversation)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的个人信息提取助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    "format": "json",
                    "stream": False
                }
            ) as resp:
                result = await resp.json()
                facts = json.loads(result["message"]["content"])
                return facts.get("facts", [])
```

---

## 配置示例

```yaml
memory:
  retrieval_mode: fts5
  
  sqlite:
    path: ./data/xiaozhi_memory.db
  
  # LLM 配置
  llm:
    provider: ollama  # openai, ollama, zhipu
    model: qwen2:7b
    base_url: http://localhost:11434  # Ollama
    api_key: xxx  # OpenAI/智谱
    
  # 提取配置
  extraction:
    enabled: true
    max_retrieved_memories: 20  # 传入 LLM 的现有记忆数量
    max_recent_memories: 10     # 最近提取的记忆数量
    observation_date_delta: 0   # 对话日期偏移（天）
```

---

## 关键优势

| 特性 | 说明 |
|------|------|
| **单次 LLM 调用** | mem0ai V3 策略，延迟低 |
| **记忆链接** | 建立记忆间关联，提升检索 |
| **Critical Rules** | PowerMem 的核心规则 |
| **上下文丰富** | 15-80词，保留完整信息 |
| **Add-only** | 简单高效，通过检索排序 |
| **时间感知** | Observation Date 解析相对时间 |
| **多语言保持** | 禁止翻译，保持原文 |
| **意图强调** | 即使没有时间也提取意图 |

---

## 实现优先级

### Phase 1: 基础 LLM 提取
- [ ] LLM 客户端基类和 OpenAI 实现
- [ ] FACT_EXTRACTION_PROMPT
- [ ] 修改 add_memory 使用 LLM 提取
- [ ] 去重机制

### Phase 2: 记忆链接
- [ ] linked_memory_ids 支持
- [ ] 相关记忆检索（用于链接）
- [ ] 链接关系存储

### Phase 3: 多 LLM 支持
- [ ] Ollama 客户端（本地免费）
- [ ] 智谱 AI 客户端
- [ ] 其他兼容 OpenAI API 的服务

### Phase 4: 优化
- [ ] 提取缓存
- [ ] 批量提取
- [ ] 错误重试
