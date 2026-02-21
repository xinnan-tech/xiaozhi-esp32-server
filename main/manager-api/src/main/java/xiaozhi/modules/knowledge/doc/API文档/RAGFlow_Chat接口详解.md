## 1. 创建助手应用 - `create`
**接口描述**: 创建一个新的对话助手（Chat Assistant）。支持配置关联知识库、LLM 模型参数、提示词（Prompt）以及开场白等高级设置。
**请求方法**: `POST`
**接口地址**: `/api/v1/chats`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| name | string | 是 | - | 助手应用名称 (租户内唯一) |
| avatar | string | 否 | - | 助手头像 (URL 或 Base64 字符串) |
| description | string | 否 | "A helpful Assistant" | 助手的功能描述 |
| dataset_ids | array | 否 | [] | 关联的知识库 ID 列表 (必须是当前租户有权限访问的知识库) |
| llm | object | 否 | - | LLM 模型生成配置 (如模型名称、温度等) |
| prompt | object | 否 | - | 提示词引擎与检索配置 (包含 System Prompt, Opener, Rerank 等) |

**`llm` 对象详细结构**:
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| model_name | string | 是 | - | 模型名称 (例如: `deepseek-chat`, `gpt-4`, `qwen-turbo`) |
| temperature | float | 否 | 0.1 | 温度系数 (0.0 ~ 1.0)，越高越随机，越低越确定 |
| top_p | float | 否 | 0.3 | 核采样概率阈值 |
| max_tokens | int | 否 | 512 | 单次回答的最大 Token 数限制 |
| presence_penalty | float | 否 | 0.4 | 话题新鲜度惩罚 (-2.0 ~ 2.0)，正值鼓励讨论新话题 |
| frequency_penalty | float | 否 | 0.7 | 频率惩罚 (-2.0 ~ 2.0)，正值减少重复词汇 |

**`prompt` 对象详细结构**:
*注意：此对象包含“提示词配置”与“检索策略配置”两部分。*

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| prompt | string | 否 | (内置默认提示词) | **System Prompt (系统提示词)**。给大模型的角色指令，例如 "你是一个客服..."。可使用变量占位符 `{knowledge}`。 |
| opener | string | 否 | "Hi! I'm your assistant..." | **开场白**。用户进入对话窗口时，助手自动发送的第一条欢迎语。 |
| show_quote | boolean | 否 | true | **显示引用**。回答中是否标注来源文档 (e.g., [1])。 |
| variables | array | 否 | `[{"key": "knowledge", "optional": false}]` | **变量列表**。定义用于填充 System Prompt 的变量。`knowledge` 为保留变量，代表检索到的知识片段。 |
| rerank_model | string | 否 | - | **重排序模型 ID**。配置后会对检索结果进行二次精排 (如 `BAAI/bge-reranker-v2-m3`)。 |
| keywords_similarity_weight | float | 否 | 0.7 | **关键字权重** (0.0 ~ 1.0)。控制混合检索的比例。更接近 1.0 侧重关键字匹配，更接近 0.0 侧重向量语义匹配。 |
| similarity_threshold | float | 否 | 0.2 | **相似度阈值** (0.0 ~ 1.0)。低于此相似度的文档块将被过滤，不喂给大模型。 |
| top_n | int | 否 | 6 | **Top N**。最终截取并输入给大模型的文档块数量。 |
| empty_response | string | 否 | "Sorry! No relevant..." | **空结果回复**。当没有检索到相关知识库内容时的兜底回复。 |
| tts | boolean | 否 | false | **启用 TTS**。是否将助手的文本回答自动转为语音播放。 |
| refine_multiturn | boolean | 否 | true | **多轮对话优化**。是否根据历史上下文重写用户问题 (Query Rewrite) 以提高检索准确率。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "e0d34e2c-1234-5678-9xxx-xxxxxxxxxxxx",
    "name": "企业知识库助手",
    "avatar": "http://example.com/avatar.png",
    "description": "用于回答员工内部问题的 AI",
    "dataset_ids": ["kb_123", "kb_456"],
    "llm": {
      "model_name": "deepseek-chat",
      "temperature": 0.1,
      "top_p": 0.3,
      "max_tokens": 512,
      "presence_penalty": 0.4,
      "frequency_penalty": 0.7
    },
    "prompt": {
      "prompt": "你是一个智能助手，请根据以下知识回答问题：\n{knowledge}",
      "opener": "你好！有什么可以帮你的？",
      "show_quote": true,
      "variables": [
        { "key": "knowledge", "optional": false }
      ],
      "rerank_model": "",
      "keywords_similarity_weight": 0.7,
      "similarity_threshold": 0.2,
      "top_n": 8,
      "empty_response": "抱歉，知识库中没有找到相关答案。",
      "tts": false,
      "refine_multiturn": true
    },
    "create_time": 1715623400000,
    "update_time": 1715624500000
  }
}
```

---

## 2. 获取助手列表 - `list_chat`
**接口描述**: 获取当前租户下的所有助手应用列表。支持分页、排序及按名称/ID筛选。
**请求方法**: `GET`
**接口地址**: `/api/v1/chats`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 30 | 每页条数 |
| orderby | string | 否 | create_time | 排序字段 (`create_time`, `update_time`) |
| desc | boolean | 否 | true | 是否降序排列 (`true`: 降序, `false`: 升序) |
| name | string | 否 | - | 按名称模糊搜索 (支持 partial match) |
| id | string | 否 | - | 按 ID 精确筛选 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "e0d34e2c-...",
      "name": "客服机器人",
      "avatar": "http://...",
      "datasets": [
        {
          "id": "kb_1",
          "name": "产品手册",
          "avatar": "",
          "chunk_num": 100
        }
      ],
      "llm": { ... },     // (结构同 create 接口响应)
      "prompt": { ... },  // (结构同 create 接口响应)
      "create_time": 1715623400000
    }
  ]
}
```

---

## 3. 更新助手配置 - `update`
**接口描述**: 更新指定助手应用的配置信息。支持全量或增量更新部分字段。
**请求方法**: `PUT`
**接口地址**: `/api/v1/chats/<chat_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | string | 是 | 助手应用 ID |

#### Body Parameters (JSON)
*(以下所有字段均为可选，仅传递需要修改的字段即可)*

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| name | string | - | 新的助手名称 |
| avatar | string | - | 新的头像 URL 或 Base64 |
| dataset_ids | array | - | **全量替换**关联的知识库 ID 列表 |
| llm | object | - | 更新 LLM 配置。需包含 `model_name`，其他字段覆盖更新。 |
| prompt | object | - | 更新提示词配置。支持增量更新 (e.g. 只改 `opener`)。 |
| show_quotation | boolean | - | 是否显示引用来源 (此字段直接位于根对象下，对应 prompt.show_quote) |

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

## 4. 批量删除助手 - `delete_chats`
**接口描述**: 批量删除一个或多个助手应用。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/chats`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array<string> | 是 | 要删除的助手应用 ID 列表。**⚠️ 注意：若列表为空或不传，虽然后端有全量删除逻辑，但在实际业务中应严谨传递 ID。** |

**Request Example**:
```json
{
  "ids": ["chat_id_1001", "chat_id_1002"]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
     "success_count": 2, // 成功删除的数量
     "errors": []        // 失败原因列表 (如 ID 不存在)
  }
}
```
