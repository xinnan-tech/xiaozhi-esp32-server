## 1. 获取 Agent 列表 - `list_agents`
**接口描述**: 分页查询当前租户下的所有 Agent 列表，支持按 ID 或标题筛选。
**请求方法**: `GET`
**接口地址**: `/api/v1/agents`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 30 | 每页条数 |
| orderby | string | 否 | update_time | 排序字段 (create_time, update_time, title) |
| desc | boolean | 否 | True | 是否降序排列 (True: 降序, False: 升序) |
| id | string | 否 | - | 按 Agent ID 精确筛选 |
| title | string | 否 | - | 按 Agent 标题精确筛选 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "e0d34e2c-...",
      "title": "My Assistant",
      "description": "A helpful AI assistant",
      "dsl": { ... }, // Agent 的 DSL 流程定义
      "user_id": "tenant_123",
      "avatar": "", // 头像 Base64 或 URL
      "canvas_category": "Agent",
      "create_time": 1715623400000,
      "update_time": 1715624500000
    }
  ]
}
```

---

## 2. 创建 Agent - `create_agent`
**接口描述**: 创建一个新的 Agent，必须包含标题和 DSL 定义。
**请求方法**: `POST`
**接口地址**: `/api/v1/agents`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| title | string | 是 | - | Agent 的名称 (必须唯一) |
| dsl | object | 是 | - | Agent 的流程定义 (节点、连线配置) |
| description | string | 否 | - | Agent 的功能描述 |
| avatar | string | 否 | - | Agent 头像 (Base64 字符串或 URL) |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

---

## 3. 更新 Agent - `update_agent`
**接口描述**: 更新指定 Agent 的配置信息，支持增量更新（仅传递需要修改的字段）。
**请求方法**: `PUT`
**接口地址**: `/api/v1/agents/<agent_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | 要更新的 Agent ID |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| title | string | 否 | - | 新的 Agent 名称 |
| dsl | object | 否 | - | 新的 DSL 流程定义 |
| description | string | 否 | - | 新的功能描述 |
| avatar | string | 否 | - | 新的头像 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

---

## 4. 删除 Agent - `delete_agent`
**接口描述**: 根据 ID 删除指定的 Agent。此操作不可恢复。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/agents/<agent_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | 要删除的 Agent ID |

#### Body Parameters (JSON)
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

---

## 5. Webhook 测试触发 - `webhook`
**接口描述**: 用于测试 Agent 的 Webhook 触发功能。该接口模拟外部系统调用，触发 Agent 按照配置的 "Begin" 节点逻辑开始执行。支持同步等待结果或流式返回（取决于 Agent 配置）。
**请求方法**: `POST` (支持 GET/PUT/DELETE 等，取决于 Canvas 配置)
**接口地址**: `/api/v1/webhook_test/<agent_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | Agent 的唯一标识符 |

#### Query / Headers / Body Parameters
**说明**: 此接口的参数完全动态，取决于 Agent 画布中 **"Begin" (开始)** 节点的 **Webhook** 配置。
- 如果配置了 Query 参数验证，则需在 URL 中传递对应参数。
- 如果配置了 Header 验证，则需传递对应 Header。
- **Body**: 通常为 JSON 格式，包含 Agent 运行所需的变量（inputs）或上下文数据。

**Body Example (JSON)**:
```json
{
  "inputs": {
    "topic": "AI Trends",
    "style": "professional"
  },
  "query": "Start generation"
}
```

### 响应参数 (Response)
**Content-Type**: `application/json` (或 `text/event-stream`)

**即时响应模式 (Immediately)**:
```json
{
  "code": 0,
  "data": {
    "content": "生成的回答内容...",
    "usage": { ... }
  }
}
```

**流式响应模式 (SSE)**:
如果不使用 `webhook_test` 而是生产环境 `webhook` 且配置为 SSE，则返回流式数据。但在 `webhook_test` 接口中，通常配合 `webhook_trace` 进行异步调试。

---

## 6. Webhook 执行轨迹查询 - `webhook_trace`
**接口描述**: 轮询查询 Agent 在 Webhook 测试触发后的执行日志和中间状态。采用长轮询或游标机制，实时获取执行进度。
**请求方法**: `GET`
**接口地址**: `/api/v1/webhook_trace/<agent_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| agent_id | string | 是 | Agent 的唯一标识符 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| since_ts | float | 否 | 当前时间 | 起始时间戳。返回此时间之后的日志事件。首次调用可不传（获取当前时间作为游标）。 |
| webhook_id | string | 否 | - | Webhook 会话 ID。用于锁定特定的某次执行记录。首次轮询时不传，接口会返回新生成的 ID。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "webhook_id": "YWdlbnxxxx...",  // 当前追踪的会话 ID (加密串)
    "finished": false,              // 执行是否已结束 (true/false)
    "next_since_ts": 1715629999.5,  // 下一次轮询应使用的 since_ts
    "events": [                     // 本次轮询获取到的新事件列表
      {
        "ts": 1715629998.1,
        "event": "message",         // 事件类型: message, start_to_think, finished, error 等
        "data": {
            "content": "思考中...",
            "reference": []
        }
      }
    ]
  }
}
```

### 💡 最佳实践 (调试流程)
1.  **初始化**: 调用 `GET /webhook_trace/<id>` (不带参数)，获取 `next_since_ts` (记为 `T0`)。
2.  **触发**: 调用 `POST /webhook_test/<id>` 发送测试数据。
3.  **首帧捕获**: 循环调用 `GET /webhook_trace/<id>?since_ts=T0`，直到返回 `webhook_id` (记为 `WID`) 和第一批 `events`。
4.  **持续追踪**: 使用 `WID` 和响应中的 `next_since_ts` 持续轮询，直到 `data.finished == true`。
