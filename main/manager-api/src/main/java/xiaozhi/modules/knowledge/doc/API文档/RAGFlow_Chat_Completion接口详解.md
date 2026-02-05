# RAGFlow 对话交互接口详解 (Chat Completion & OpenAI Compatibility)

## 5. 对话助手对话 (流式) - `chat_completion`
**接口描述**: 发送问题给对话助手 (Assistant/Chat) 并获取回复。这是 RAGFlow 最核心的原生对话接口，支持 **Server-Sent Events (SSE)** 流式响应。它会根据助手绑定的知识库进行 RAG 检索生成。
**请求方法**: `POST`
**接口地址**: `/api/v1/chats/<chat_id>/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| session_id | string | 是 | - | **会话 ID**。从 `create_chat_session` 获取。 |
| question | string | 是 | - | **用户问题**。 |
| stream | boolean | 否 | true | **是否流式响应**。 |
| quote | boolean | 否 | false | **返回引用**。是否在响应中包含检索到的引用片段。 |
| doc_ids | string | 否 | - | **限定文档 ID**。多个 ID 用逗号分隔，仅检索指定文档。 |
| metadata_condition | object | 否 | {} | **元数据过滤**。用于限定检索范围。 |

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

每一行数据以 `data:` 开头，包含一个 JSON 对象。

**Event Example**:
```text
data:{"code": 0, "message": "success", "data": {"answer": "Hello", "reference": {}}}

data:{"code": 0, "message": "success", "data": {"answer": " world!", "reference": {}}}

data:{"code": 0, "message": "success", "data": {"answer": "", "reference": {"chunk_1": {...}}}} // 引用数据
```

### 响应参数 (Non-Stream Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "Hello world! This is the generated response.",
    "reference": {
      "chunk_id_1": {
        "content_with_weight": "Original text...",
        "doc_name": "manual.pdf"
      }
    }
  }
}
```

---

## 6. OpenAI 兼容对话 - `chat_completion_openai_like`
**接口描述**: 提供与 **OpenAI API (`/v1/chat/completions`)** 完全兼容的接口。允许开发者使用 LangChain、OpenAI Python SDK 或其他支持 OpenAI 协议的工具直接调用 RAGFlow，实现无缝迁移。
**请求方法**: `POST`
**接口地址**: `/api/v1/chats_openai/<chat_id>/chat/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID**。在此上下文中充当 "Base URL" 的一部分。 |

#### Body Parameters (JSON - OpenAI Standard)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| messages | array | 是 | **消息列表**。包含 `role` (system/user/assistant) 和 `content`。 |
| model | string | 是 | **模型名称**。可以是任意非空字符串 (RAGFlow 会使用助手预设的模型)。 |
| stream | boolean | 否 | **是否流式**。默认为 `true`。 |

**Request Example**:
```json
{
  "model": "ragflow_default",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum physics."}
  ],
  "stream": true
}
```

### 响应参数 (Stream Response - OpenAI Format)
**Content-Type**: `text/event-stream`

严格遵循 OpenAI Chunk 格式：

```text
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1715000000, "model": "model", "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1715000001, "model": "model", "choices": [{"index": 0, "delta": {"content": "Quantum"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1715000002, "model": "model", "choices": [{"index": 0, "delta": {"content": " physics"}, "finish_reason": null}]}

data: [DONE]
```

---

## 7. 嵌入式 Chatbot 对话 - `chatbot_completions`
**接口描述**: 专为 **嵌入式窗口 (Embed Window)** 设计的公开对话接口。它通常用于将 RAGFlow 助手作为客服窗口嵌入到第三方网站。与普通接口不同，它通过 `Authorization` Header 传递 **Beta Token** (即 API Key) 进行鉴权，且通常面向最终用户。
**请求方法**: `POST`
**接口地址**: `/api/v1/chatbots/<dialog_id>/completions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dialog_id | string | 是 | **助手 ID** (Dialog ID)。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| question | string | 是 | - | **用户问题**。 |
| stream | boolean | 否 | true | **是否流式**。 |
| session_id | string | 否 | - | **会话 ID**。用于维持上下文。 |
| quote | boolean | 否 | false | **返回引用**。 |

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

与 `chat_completion` 类似，返回 RAGFlow 原生 SSE 格式。

```text
data:{"code": 0, "message": "success", "data": {"answer": "Here is the answer...", "reference": {}}}
```

---

## 8. Chatbot 初始化信息 - `chatbots_inputs`
**接口描述**: 获取嵌入式 Chatbot 的初始化配置信息。通常在前端组件加载时调用，用于展示助手的头像、名称、开场白 (Prologue) 等信息。
**请求方法**: `GET`
**接口地址**: `/api/v1/chatbots/<dialog_id>/info`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dialog_id | string | 是 | **助手 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "title": "IT Support Bot",          // 助手名称
    "avatar": "http://...",             // 头像 URL
    "prologue": "Hi! How can I help?"   // 开场白
  }
}
```
