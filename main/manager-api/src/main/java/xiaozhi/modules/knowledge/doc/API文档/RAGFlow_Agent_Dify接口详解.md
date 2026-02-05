# RAGFlow Agent 与 Dify 兼容接口详解 (Agent & Dify Compatibility)

## 1. Dify 兼容检索 - `retrieval`
**接口描述**: 模拟 Dify API 格式的知识库检索接口。此接口主要用于让现有的 Dify 客户端或系统能够方便地接入 RAGFlow 的知识库检索能力。它支持文本检索、混合检索以及通过元数据过滤文档。
**请求方法**: `POST`
**接口地址**: `/api/v1/dify/retrieval`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| knowledge_id | string | 是 | - | **知识库 ID**。 |
| query | string | 是 | - | **查询文本**。用户输入的检索问题。 |
| use_kg | boolean | 否 | false | **使用知识图谱**。是否结合知识图谱进行检索。 |
| retrieval_setting | object | 否 | {} | **检索配置**。包含相似度阈值和 Top-K。 |
| metadata_condition | object | 否 | {} | **元数据过滤条件**。用于筛选特定文档。 |

#### 参数详情 (Detail Objects)
**retrieval_setting**:
```json
{
  "score_threshold": 0.5, // 相似度阈值 (default: 0.0)
  "top_k": 5              // 返回数量 (default: 1024)
}
```

**metadata_condition**:
```json
{
  "logic": "and", // 逻辑关系 (and/or)
  "conditions": [
    {
      "name": "author",           // 字段名
      "comparison_operator": "eq",// 运算符 (eq, ne, gt, lt 等)
      "value": "Alice"            // 字段值
    }
  ]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "records": [
      {
        "content": "RAGFlow 是一个基于深度文档理解的检索增强生成引擎...",
        "score": 0.92,
        "title": "RAGFlow_Introduction.pdf",
        "metadata": {
          "doc_id": "doc_uuid_123",
          "author": "Alice",
          "publish_year": "2024"
        }
      },
      {
        "content": "DeepDOC 模型能够精准识别复杂的表格结构...",
        "score": 0.88,
        "title": "DeepDOC_Tech_Report.pdf",
        "metadata": {
          "doc_id": "doc_uuid_456",
          "author": "Bob"
        }
      }
    ]
  }
}
```

---

## 2. 创建 Agent 会话 - `create_agent_session`
**接口描述**: 创建一个新的 Agent 会话 (Session)。会话是用户与 Agent 交互的上下文容器，保存了历史对话记录和 DSL（领域特定语言）状态。
**请求方法**: `POST`
**接口地址**: `/api/v1/agents/<agent_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| user_id | string | 否 | **用户标识**。用于区分不同终端用户的会话。若不传，默认为当前 Tenant ID。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "session_uuid_new_123",
    "agent_id": "agent_uuid_abc",
    "user_id": "user_123",
    "source": "agent",
    "dsl": { ... }, // 完整的 Agent DSL 定义
    "messages": [
      {
        "role": "assistant",
        "content": "你好！我是你的智能助手，有什么可以帮你的吗？" // Prologue (开场白)
      }
    ]
  }
}
```

---

## 3. 获取 Agent 会话列表 - `list_agent_session`
**接口描述**: 分页获取指定 Agent 下的会话列表。支持按 ID 或 User ID 过滤。
**请求方法**: `GET`
**接口地址**: `/api/v1/agents/<agent_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | **页码**。 |
| page_size | int | 否 | 30 | **每页数量**。 |
| orderby | string | 否 | "update_time" | **排序字段**。 |
| desc | boolean | 否 | true | **是否降序**。 |
| id | string | 否 | - | **会话 ID**。精确筛选。 |
| user_id | string | 否 | - | **用户标识**。筛选特定用户的会话。 |
| dsl | boolean | 否 | true | **包含 DSL**。是否在返回结果中包含完整的 DSL 结构 (数据量较大)。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "session_uuid_123",
      "agent_id": "agent_uuid_abc",
      "user_id": "user_123",
      "create_time": 1715000000000,
      "update_time": 1715000050000,
      "source": "agent",
      "messages": [
        {
          "role": "assistant",
          "content": "Hi there!"
        },
        {
          "role": "user",
          "content": "What is RAG?"
        }
      ]
    }
  ]
}
```

---

## 4. 删除 Agent 会话 - `delete_agent_session`
**接口描述**: 批量删除 Agent 会话。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/agents/<agent_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array<string> | 否 | **会话 ID 列表**。若不传该参数，将尝试删除(或清空)该 Agent 下的所有会话（需谨慎）。 |

**Request Example**:
```json
{
  "ids": ["session_id_1", "session_id_2"]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "success_count": 2,
    "errors": []
  }
}
```

---

## 5. Agent 对话 (流式) - `agent_completions`
**接口描述**: 向 Agent 发送用户问题并获取回复。这是 Agent 交互的核心接口，支持 **Server-Sent Events (SSE)** 流式响应。Agent 会根据编排好的 DSL 流程执行（可能涉及多个节点、知识库检索、LLM 推理等），并实时推送执行过程和最终结果。
**请求方法**: `POST`
**接口地址**: `/api/v1/agents/<agent_id>/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| session_id | string | 是 | - | **会话 ID**。必须是 `create_agent_session` 返回的 ID。 |
| question | string | 是 | - | **用户问题**。 |
| stream | boolean | 否 | true | **是否流式响应**。强烈建议设为 `true` 以获得更好的用户体验。 |
| return_trace | boolean | 否 | false | **返回执行轨迹**。如果为 `true`，流式响应中将包含各个节点的执行过程数据 (Trace)。 |

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

响应是一个 SSE 流，每一行以 `data:` 开头，包含一个 JSON 对象。

**Event Types**:
- `message`: 普通文本消息片段。
- `node_finished`: (当 `return_trace=true` 时) 节点执行完成事件，包含节点输出数据。
- `message_end`: 消息结束。
- `[DONE]`: 流结束标志。

#### Stream Chunk Examples:

**1. 文本生成片段 (message)**:
```text
data:{"code": 0, "message": "success", "data": {"content": "Hello", "reference": {}, "id": "msg_uuid_1"}, "event": "message"}

data:{"code": 0, "message": "success", "data": {"content": " world", "reference": {}, "id": "msg_uuid_1"}, "event": "message"}
```

**2. 节点执行轨迹 (node_finished, return_trace=true)**:
```text
data:{"code": 0, "message": "success", "data": {"component_id": "retrieval_node_1", "content": "...", "trace": [...]}, "event": "node_finished"}
```

**3. 最终结束 (DONE)**:
```text
data:[DONE]
```

#### Non-Stream Response (stream=false)
如果不使用流式响应，将等待 Agent 全流程执行完毕后一次性返回 JSON。

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "content": "Hello world! This is the final answer.",
    "reference": {
        "chunk_id_1": { ... } // 引用来源
    },
    "trace": [ ... ] // 如果 return_trace=true
  }
}
```
