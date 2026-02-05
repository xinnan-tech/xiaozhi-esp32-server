## 1. 创建知识库 - `create`
**接口描述**: 创建一个新的知识库（Dataset），用于存储和检索文档数据。支持配置嵌入模型（Embedding Model）、解析方法、权限范围等。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| name | string | 是 | - | **知识库名称**。在同一个租户（Tenant）内必须唯一。 |
| avatar | string | 否 | "" | **知识库头像**。Base64 编码的图片字符串。 |
| description | string | 否 | "" | **描述信息**。用于说明知识库的用途或内容概要。 |
| embedding_model | string | 否 | (系统默认) | **嵌入模型名称** (例如 `BAAI/bge-large-zh-v1.5`)。若不传，则自动使用系统设置的默认 Embedding 模型。 |
| permission | string | 否 | "me" | **可见权限**。`me`: 仅自己可见；`team`: 团队内所有成员可见。 |
| chunk_method | string | 否 | "naive" | **默认分块解析方法**。当上传文件未指定解析方式时使用。可选值: `naive` (通用), `manual` (手动), `qa` (Q&A拆分), `table` (表格), `paper` (论文), `book` (书籍), `laws` (法律), `presentation` (PPT), `picture` (图片), `one` (单文档), `email` (邮件)。 |
| parser_config | object | 否 | (见下文) | **解析器详细配置**。根据 `chunk_method` 的不同而变化。 |

**`parser_config` 默认配置参数 (Naive 通用模式)**:
| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| chunk_token_num | int | 512 | **切片最大 Token 数**。超过该长度会被截断到下一块。 |
| delimiter | string | "\\n" | **分段分隔符**。用于识别段落边界。 |
| layout_recognize | string | "DeepDOC" | **布局识别模型**。用于处理复杂文档结构 (如 `DeepDOC` 或 `Simple`)。 |
| html4excel | boolean | false | **Excel转HTML**。是否将 Excel 表格转为 HTML 格式进行解析。 |
| auto_keywords | int | 0 | **自动关键词抽取**。0 表示不抽取；N>0 表示为每个切片抽取 N 个关键词。 |
| auto_questions | int | 0 | **自动问题生成**。0 表示不生成；N>0 表示为每个切片生成 N 个相关问题。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "kb_uuid_12345678",
    "name": "企业产品手册",
    "avatar": "",
    "tenant_id": "tenant_001",
    "description": "存放所有产品相关的说明文档",
    "embedding_model": "BAAI/bge-large-zh-v1.5",
    "permission": "me",
    "chunk_method": "naive",
    "parser_config": {
      "chunk_token_num": 512,
      "delimiter": "\n",
      "layout_recognize": "DeepDOC",
      "html4excel": false,
      "auto_keywords": 0,
      "auto_questions": 0
    },
    "chunk_count": 0,
    "document_count": 0,
    "create_time": 1715623400000,
    "update_time": 1715624500000
  }
}
```

---

## 2. 删除知识库 - `delete`
**接口描述**: 批量删除一个或多个知识库。删除知识库将连带删除其中的所有文档和索引数据，**不可恢复**。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/datasets`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array<string> | 是 | **ID 列表**。指定要删除的知识库 ID。如果传递 `null`，则会**清空当前租户下所有**知识库（高危操作，请谨慎使用）。 |

**Request Example**:
```json
{
  "ids": ["kb_id_101", "kb_id_102"]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "Successfully deleted 2 datasets, 0 failed...",
  "data": {
     "success_count": 2, // 成功删除的数量
     "errors": []        // 失败的 ID 及原因列表
  }
}
```

---

## 3. 获取知识库列表 - `list_datasets`
**接口描述**: 获取当前用户（及团队）有权限访问的知识库列表。支持分页、排序和筛选。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
无

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | **页码**。从 1 开始。 |
| page_size | int | 否 | 30 | **每页条数**。 |
| orderby | string | 否 | "create_time" | **排序字段**。可选值: `create_time` (创建时间), `update_time` (更新时间), `document_count` (文档数)。 |
| desc | boolean | 否 | true | **是否降序**。`true`: 降序 (最新的在前); `false`: 升序。 |
| name | string | 否 | - | **名称筛选**。支持模糊匹配。 |
| id | string | 否 | - | **ID 筛选**。精确匹配知识库 ID。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "kb_uuid_123",
      "name": "HR 政策库",
      "document_count": 12,    // 包含的文档数量
      "token_num": 10240,      // 总 Token 数
      "chunk_count": 150,      // 总切片数
      "create_time": 1715623400000,
      "permission": "team",
      "embedding_model": "BAAI/bge-large-zh-v1.5"
    }
  ],
  "total": 1 // 匹配查询条件的总记录数 (用户分页计算)
}
```

---

## 4. 更新知识库配置 - `update`
**接口描述**: 更新指定知识库的配置信息。注意：如果知识库内已有解析过的切片，通常不允许修改嵌入模型 (`embedding_model`)。
**请求方法**: `PUT`
**接口地址**: `/api/v1/datasets/<dataset_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Body Parameters (JSON)
*(以下所有字段均为可选，仅传递需要修改的字段即可)*

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| name | string | - | **新名称**。需保持租户内唯一。 |
| avatar | string | - | **新头像**。Base64 字符串。 |
| description | string | - | **新描述**。 |
| permission | string | - | **新权限**。`me` 或 `team`。 |
| embedding_model | string | - | **嵌入模型**。**注意**: 仅当知识库为空（chunk_count=0）时才允许修改。 |
| chunk_method | string | - | **默认解析方法**。修改后将应用于后续新上传的文件 (旧文件解析方式不变)。 |
| parser_config | object | - | **解析器配置**。全量覆盖旧配置 (结构参考 create 接口)。 |
| pagerank | int | 0 | **PageRank 权重**。仅在使用 Elasticsearch 引擎且需调整图谱权重时设置。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
      "id": "kb_uuid_...",
      "name": "新名称",
      "update_time": 1715629999000,
      ...
  }
}
```

---

## 5. 获取知识图谱数据 - `knowledge_graph`
**接口描述**: 获取知识库构建的知识图谱数据，包含节点（Nodes）和边（Edges），用于前端可视化展示（如 ECharts 力导向图）。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/knowledge_graph`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Query Parameters
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "graph": {
      "nodes": [
        {
          "id": "node_1",
          "label": "人工智能",      // 节点显示的文本
          "pagerank": 0.05,       // PageRank 权重 (决定节点大小)
          "color": "#fcb",        // 节点颜色
          "img": ""               // 节点图标 (如有)
        },
        {
          "id": "node_2",
          "label": "机器学习",
          "pagerank": 0.03,
          "color": "#e2b"
        }
      ],
      "edges": [
        {
          "source": "node_1",     // 起始节点 ID
          "target": "node_2",     // 目标节点 ID
          "weight": 0.8,          // 边权重 (决定连线粗细)
          "label": "includes"     // 关系名称 (显示在连线上)
        }
      ]
    },
    "mind_map": {                 // 思维导图结构的保留字段 (通常用于脑图展示)
        "root": {
            "id": "root_node",
            "children": [...]
        }
    }
  }
}
```

---

## 6. 清空知识图谱数据 - `delete_knowledge_graph`
**接口描述**: 删除指定知识库中已生成的知识图谱索引数据（包括所有实体节点和关系边）。
**注意**: 此操作**不会**删除原始文档或普通的向量索引，仅仅是重置图谱结构。如果需要重新生成图谱，请再次调用 `chunk` 相关接口或使用 `run_graphrag`。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/datasets/<dataset_id>/knowledge_graph`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Body Parameters
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

## 7. 运行/触发 GraphRAG 索引任务 - `run_graphrag`
**接口描述**: 触发后台异步任务，对知识库中的文档进行 GraphRAG 索引构建。此过程会使用 LLM 抽取实体（Entities）和关系（Relationships），并构建全局社区摘要。
**前提条件**: 知识库中必须包含已解析的文档。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/run_graphrag`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Body Parameters (JSON)
*(Body 可为空 `{}`, 后续版本将扩展以下配置参数)*

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| entity_types | array | ["organization", "person", "geo", "event"] | **(预留)** 指定要抽取的实体类型列表。 |
| method | string | "light" | **(预留)** 构建模式: `light` (轻量级), `general` (标准), `complex` (深度)。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "graphrag_task_id": "task_uuid_12345678" // 异步任务 ID，用于后续追踪进度
  }
}
```

---

## 8. 运行/触发 RAPTOR 递归摘要任务 - `run_raptor`
**接口描述**: 触发后台异步任务，对知识库中的文档运行 RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 算法。
**功能说明**: 该算法会递归地对文档块进行聚类和摘要，生成多层级的树状索引，显著提升对长文档和复杂问题的回答能力。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/run_raptor`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Body Parameters (JSON)
*(Body 可为空 `{}`, 后续版本将扩展以下配置参数)*

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| max_cluster | int | 64 | **(预留)** 最大聚类数。 |
| prompt | string | (内置摘要提示词) | **(预留)** 用于生成摘要的 Prompt。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "raptor_task_id": "task_uuid_87654321" // 异步任务 ID
  }
}
```

---

## 9. 查询 GraphRAG 任务进度 - `trace_graphrag`
**接口描述**: 查询指定知识库当前 **GraphRAG** 索引构建任务的实时状态。支持长轮询机制监测进度。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/trace_graphrag`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Query Parameters
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "task_uuid_12345678",        // 任务 ID
    "doc_id": "doc_uuid_...",          // 当前正在处理的文档 ID (如果是多文档任务)
    "from_page": 0,                    // 当前处理的起始页码
    "to_page": 10,                     // 当前处理的结束页码
    "progress": 0.45,                  // **总进度** (0.0 ~ 1.0)。0.0: 未开始/刚开始; 1.0: 完成; -1.0: 失败。
    "progress_msg": "Extracting entities from chunk 25...", // **当前状态描述**。用于前端展示 Loading 提示。
    "create_time": 1715623400000,
    "update_time": 1715624500000
  }
}
```

---

## 10. 查询 RAPTOR 任务进度 - `trace_raptor`
**接口描述**: 查询指定知识库当前 **RAPTOR** 递归摘要任务的实时状态。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/trace_raptor`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | 知识库 ID |

#### Query Parameters
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "task_uuid_87654321",
    "progress": 1.0,                   // 进度值。1.0 表示树构建完成。
    "progress_msg": "Tree construction completed.", // 状态消息。
    "create_time": 1715629000000
  }
}
```
