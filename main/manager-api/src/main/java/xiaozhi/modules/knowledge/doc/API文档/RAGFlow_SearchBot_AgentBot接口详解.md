# RAGFlow 搜索机器人 & AgentBot 接口详解 (SearchBot & AgentBot)

## 1. 搜索机器人对话 - `ask_about_embedded`
**接口描述**: 面向 **SearchBot (搜索机器人)** 的核心对话接口，通常用于嵌入式知识库问答场景。与普通 Chat 不同，它更侧重于从指定的 `kb_ids` 中直接检索答案，且鉴权使用 `Authorization: Bearer <Beta_Token>` (即 API Key)。
**请求方法**: `POST`
**接口地址**: `/api/v1/searchbots/ask`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| question | string | 是 | - | **用户问题**。 |
| kb_ids | array<string> | 是 | - | **知识库 ID 列表**。限定从哪些知识库中检索。 |
| search_id | string | 否 | - | **搜索应用 ID**。如果指定，将使用该搜索应用的配置 (Search App Config)。 |

**Request Example**:
```json
{
  "question": "What is the refund policy?",
  "kb_ids": ["dataset_uuid_1", "dataset_uuid_2"],
  "search_id": "search_app_uuid_abc"
}
```

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

```text
data:{"code": 0, "message": "", "data": {"answer": "According to the ", "reference": {}}}

data:{"code": 0, "message": "", "data": {"answer": "policy, refunds are processed within 7 days.", "reference": {"chunk_1": {"content_with_weight": "Refunds...", "doc_name": "policy.pdf"}}}}

data:{"code": 0, "message": "", "data": true} // 结束标志
```

---

## 2. 获取思维导图 - `mindmap`
**接口描述**: 根据用户的查询或对话上下文，生成用于前端展示的思维导图数据结构。这通常用于帮助用户梳理复杂的搜索结果或知识结构。
**请求方法**: `POST`
**接口地址**: `/api/v1/searchbots/mindmap`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| question | string | 是 | **用户问题/主题**。 |
| kb_ids | array<string> | 是 | **知识库 ID 列表**。 |
| search_id | string | 否 | **搜索应用 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "root": {
      "text": "Refund Policy", // 根节点文本
      "children": [
        {
          "text": "Conditions",
          "children": [
            { "text": "Product defect" },
            { "text": "Shipping error" }
          ]
        },
        {
          "text": "Timeline",
          "children": [
            { "text": "7-14 business days" }
          ]
        }
      ]
    }
  }
}
```

---

## 3. 获取相关推荐问题 - `related_questions_embedded`
**接口描述**: 根据用户当前的问题，生成一组相关的推荐问题 (Suggest Questions)。常用于搜索结果页底部的“猜你想问”。
**请求方法**: `POST`
**接口地址**: `/api/v1/searchbots/related_questions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| question | string | 是 | **用户当前问题**。 |
| search_id | string | 否 | **搜索应用 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    "How to apply for a refund online?",
    "What items are non-refundable?",
    "Contact customer support"
  ]
}
```

---

## 4. 获取 AgentBot 输入项 - `begin_inputs`
**接口描述**: 获取 **AgentBot** (嵌入式 Agent) 的初始化信息，特别是前置输入项 (Prolog/Inputs)。这用于在用户开始对话前，展示一个表单让用户输入必要信息（如姓名、邮箱、API Key 等），这些信息会被传递给 Agent 的 `Begin` 节点。
**请求方法**: `GET`
**接口地址**: `/api/v1/agentbots/<agent_id>/inputs`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "title": "Booking Assistant",
    "avatar": "http://...",
    "prologue": "Welcome! Please tell me your details.",
    "inputs": { // `Begin` 节点定义的输入变量
      "user_name": {
        "type": "string",
        "description": "Your Name",
        "required": true
      },
      "email": {
        "type": "string",
        "description": "Contact Email",
        "required": false
      }
    },
    "mode": "chat"
  }
}
```

---

## 5. AgentBot 对话交互 - `agent_bot_completions`
**接口描述**: 面向 **AgentBot** 的嵌入式对话接口。与 `agent_completions` 类似，但它专为无需登录的 C 端用户设计，通过 API Key 鉴权。它支持完整的 Agent 流程执行和流式响应。
**请求方法**: `POST`
**接口地址**: `/api/v1/agentbots/<agent_id>/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| session_id | string | 是 | **会话 ID**。 |
| inputs | object | 否 | **前置输入值**。对应 `begin_inputs` 中定义的变量，如 `{"user_name": "Alice"}`。 |
| query | string | 否 | **用户输入**。 |
| stream | boolean | 否 | **是否流式**。默认 `true`。 |

**Request Example**:
```json
{
  "session_id": "session_uuid_123",
  "inputs": {
    "user_name": "Bob"
  },
  "query": "I want to book a room.",
  "stream": true
}
```

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

```text
data:{"event": "message", "data": {"content": "Hello Bob, ", "reference": {}}}

data:{"event": "message", "data": {"content": "when do you want to check in?", "reference": {}}}
```

---

## 6. Agent OpenAI 兼容接口 - `agents_completion_openai_compatibility`
**接口描述**: 专门针对 Agent 的 **OpenAI 兼容** 接口。这使得外部工具可以像调用 OpenAI Chat Completion 一样调用 RAGFlow 配置好的复杂 Agent。
**请求方法**: `POST`
**接口地址**: `/api/v1/agents_openai/<agent_id>/chat/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | **Agent ID**。 |

#### Body Parameters (OpenAI Standard)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| messages | array | 是 | 包含 `role`, `content` 的消息数组。 |
| model | string | 是 | 占位符，任意字符串。 |
| stream | boolean | 否 | 默认 `true`。 |

### 响应参数 (Stream Response - OpenAI Format)
**Content-Type**: `text/event-stream`

```text
data: {"id": "agent-chat-uuid", "object": "chat.completion.chunk", "created": 1715000000, "model": "ragflow_agent", "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": null}]}

data: {"id": "agent-chat-uuid", "object": "chat.completion.chunk", "created": 1715000001, "model": "ragflow_agent", "choices": [{"index": 0, "delta": {"content": "Processing your request..."}, "finish_reason": null}]}

data: [DONE]
```
