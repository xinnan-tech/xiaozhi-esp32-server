# RAGFlow SearchBot 补充与通用会话接口详解 (Session Extras)

## 1. 获取引用详情 - `detail_share_embedded`
**接口描述**: 当用户点击 SearchBot 回复中的引用标号 (e.g., [1]) 时，调用此接口获取该引用的详细内容（包括原文片段、来源文档名等）。此接口通常用于前端展示“引用来源”侧边栏或弹窗。它使用 API Key (Beta Token) 进行鉴权。
**请求方法**: `GET`
**接口地址**: `/api/v1/searchbots/detail`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Query Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| search_id | string | 是 | **搜索应用/SearchBot ID**。此接口需要验证调用者是否有权访问该 SearchBot。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "search_app_uuid_123",
    "title": "IT Knowledge Base",
    "description": "Tech support search bot",
    "kb_ids": ["kb_uuid_1", "kb_uuid_2"],
    "search_config": {
      "top_k": 5,
      "similarity_threshold": 0.5
    },
    // 注意：此接口目前主要返回 Search App 的详情配置，
    // 前端通常使用 search_config 或其他信息来辅助展示引用。
    // 具体引用内容的文本通常已包含在 `ask` 接口的 `reference` 字段中。
  }
}
```

---

## 2. SearchBot 检索测试 - `retrieval_test_embedded`
**接口描述**: 面向 SearchBot 的**检索效果测试**接口。它不通过 LLM 生成答案，而是直接返回 RAG 检索到的文档片段 (`chunks`)。这用于调试 SearchBot 的检索参数（如相似度阈值、Top-K）是否合理。
**请求方法**: `POST`
**接口地址**: `/api/v1/searchbots/retrieval_test`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| kb_id | string/array | 是 | - | **知识库 ID** (或列表)。支持单个 ID 字符串或 ID 列表。 |
| question | string | 是 | - | **测试查询词**。 |
| page | int | 否 | 1 | **页码**。 |
| size | int | 否 | 30 | **每页数量**。 |
| doc_ids | array<string> | 否 | - | **限定文档 ID**。仅在指定文档中检索。 |
| similarity_threshold | float | 否 | 0.0 | **相似度阈值**。 |
| top_k | int | 否 | 1024 | **Top-K 数量**。 |
| highlight | boolean | 否 | false | **高亮匹配**。是否在返回内容中标记匹配关键词。 |

**Request Example**:
```json
{
  "kb_id": ["dataset_uuid_1"],
  "question": "refund policy",
  "top_k": 5,
  "highlight": true
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 12, // 命中总是
    "chunks": [
      {
        "content_with_weight": "Refunds are processed within <em>7 days</em>...", // 支持高亮
        "doc_name": "policy.pdf",
        "doc_id": "doc_uuid_101",
        "similarity": 0.92,
        "img_id": ""
      },
      {
        "content_with_weight": "Product return guidelines...",
        "doc_name": "guidelines.docx",
        "doc_id": "doc_uuid_102",
        "similarity": 0.88
      }
    ],
    "labels": [] // 如果启用了查询标签功能
  }
}
```

---

## 3. 通用会话问答 - `ask_about`
**接口描述**: **内部/测试用**的通用会话问答接口。与 `ask_embedded` 不同，此接口通常用于 RAGFlow 控制台内部的“调试”或“预览”功能，鉴权依赖用户的登录 Token (User Token)，且必须显式指定 `dataset_ids`。它不绑定特定的 Chat/Agent/SearchBot 配置。
**请求方法**: `POST`
**接口地址**: `/api/v1/sessions/ask`
**鉴权方式**: Header `Authorization: Bearer <USER_TOKEN>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| question | string | 是 | **用户问题**。 |
| dataset_ids | array<string> | 是 | **知识库 ID 列表**。必须是当前用户有权访问的知识库。 |

**Request Example**:
```json
{
  "question": "Summary of report",
  "dataset_ids": ["dataset_uuid_internal_1"]
}
```

### 响应参数 (Stream Response)
**Content-Type**: `text/event-stream`

```text
data:{"code": 0, "message": "", "data": {"answer": "Here is the summary:", "reference": {}}}

data:{"code": 0, "message": "", "data": {"answer": " The report indicates...", "reference": {}}}

data:{"code": 0, "message": "", "data": true} // 结束
```

---

## 4. 通用相关问题 - `related_questions`
**接口描述**: **内部/测试用**的通用相关问题推荐接口。根据用户的问题和行业背景，利用 LLM 生成推荐问题。通常用于内部测试台。
**请求方法**: `POST`
**接口地址**: `/api/v1/sessions/related_questions`
**鉴权方式**: Header `Authorization: Bearer <USER_TOKEN>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| question | string | 是 | - | **原始问题/关键词**。 |
| industry | string | 否 | "" | **行业背景** (e.g., "Finance", "Healthcare")。帮助 LLM 生成更专业的推荐。 |

**Request Example**:
```json
{
  "question": "Data privacy",
  "industry": "IT"
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    "GDPR compliance checklist",
    "Data encryption standards",
    "User consent management"
  ]
}
```
