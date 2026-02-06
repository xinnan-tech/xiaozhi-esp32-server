# RAGFlow 聊天助手会话管理接口详解 (Chat Assistant Session Management)

## 1. 创建会话 - `create_chat_session`
**接口描述**: 为指定的聊天助手 (Chat/Assistant) 创建一个新的会话。系统会自动加载该助手的开场白 (Prologue) 作为第一条消息。
**请求方法**: `POST`
**接口地址**: `/api/v1/chats/<chat_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID** (Assistant/Dialog ID)。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| name | string | 否 | "New session" | **会话名称**。 |
| user_id | string | 否 | - | **用户标识**。用于区分不同终端用户的会话。 |

**Request Example**:
```json
{
  "name": "Consulting regarding RAG",
  "user_id": "client_001"
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "session_uuid_123",
    "chat_id": "chat_uuid_abc",
    "name": "Consulting regarding RAG",
    "user_id": "client_001",
    "create_time": 1715000000000,
    "create_date": "2024-05-01 10:00:00",
    "update_time": 1715000000000,
    "update_date": "2024-05-01 10:00:00",
    "messages": [
      {
        "role": "assistant",
        "content": "Hi! I am your AI assistant. How can I help you today?" // 自动加载的开场白
      }
    ]
  }
}
```

---

## 2. 获取会话列表 - `list_chat_session`
**接口描述**: 分页获取指定助手下的会话列表。支持按名称或用户 ID 过滤。
**请求方法**: `GET`
**接口地址**: `/api/v1/chats/<chat_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID**。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | **页码**。 |
| page_size | int | 否 | 30 | **每页数量**。 |
| orderby | string | 否 | "create_time" | **排序字段**。 |
| desc | boolean | 否 | true | **是否降序**。 |
| name | string | 否 | - | **会话名称搜索**。 |
| id | string | 否 | - | **会话 ID 精确筛选**。 |
| user_id | string | 否 | - | **用户标识筛选**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "session_uuid_123",
      "chat_id": "chat_uuid_abc",
      "name": "Consulting regarding RAG",
      "user_id": "client_001",
      "create_time": 1715000000000,
      "create_date": "2024-05-01 10:00:00",
      "update_time": 1715000050000,
      "update_date": "2024-05-01 10:00:50",
      "messages": [
        {
          "role": "assistant",
          "content": "Hi! I am your AI assistant. How can I help you today?"
        },
        {
          "role": "user",
          "content": "What is RAGFlow?"
        }
      ]
    },
    {
      "id": "session_uuid_456",
      "chat_id": "chat_uuid_abc",
      "name": "New session",
      "user_id": "client_002",
      "create_time": 1714900000000,
      "create_date": "2024-04-30 09:00:00",
      "update_time": 1714900000000,
      "update_date": "2024-04-30 09:00:00",
      "messages": [ ... ]
    }
  ]
}
```

---

## 3. 更新会话 - `update_chat_session`
**接口描述**: 更新会话信息。目前主要用于 **重命名** 会话。注意：不能通过此接口修改消息记录 (`messages`)。
**请求方法**: `PUT`
**接口地址**: `/api/v1/chats/<chat_id>/sessions/<session_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID**。 |
| session_id | string | 是 | **会话 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 否 | **新的会话名称**。不可为空字符串。 |

**Request Example**:
```json
{
  "name": "RAG Technical Discussion"
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

---

## 4. 删除会话 - `delete_chat_session`
**接口描述**: 批量删除指定助手下的会话。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/chats/<chat_id>/sessions`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | **助手 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array<string> | 否 | **待删除的会话 ID 列表**。若不传该参数，将尝试删除该助手下的**所有会话**（请极其谨慎使用）。 |

**Request Example**:
```json
{
  "ids": ["session_uuid_123", "session_uuid_456"]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": null // 若全部删除成功
}
```

**Response (部分成功时)**:
```json
{
  "code": 0,
  "message": "Partially deleted 1 sessions with 1 errors",
  "data": {
    "success_count": 1,
    "errors": ["The chat doesn't own the session session_uuid_999"]
  }
}
```
