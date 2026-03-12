## 1. 上传文档 - `upload`
**接口描述**: 向指定的知识库上传一个或多个文档文件。上传后，文档将立即被存入文件系统/对象存储，并在数据库中创建记录。默认解析状态为 `UNSTART` (未开始)，解析配置将继承自 KnowledgeBase 的默认设置。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`
**Content-Type**: `multipart/form-data`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。指定文档归属的知识库。 |

#### Form Data Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | file | 是 | **文件二进制流**。支持多文件上传 (Multiple Files)。<br>支持格式: PDF, DOCX, TXT, MD, CS, HTML, CSV, XLSX, PPTX 等。<br>单文件大小限制请参考系统配置 (默认通常为 10MB/100MB)。 |
| parent_path | string | 否 | **父级目录路径**。类似于文件系统的文件夹结构，默认为 `/`。如果指定 (如 `/docs/v1/`)，文档将在该虚拟路径下列出。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "e457f92e3c0411ef8d4c0242ac120003",
      "thumbnail": null,
      "dataset_id": "d1234567890abcdef1234567890abcde",
      "chunk_method": "naive",
      "pipeline_id": null,
      "parser_config": {
        "chunk_token_num": 512,
        "delimiter": "\\n",
        "layout_recognize": "DeepDOC",
        "html4excel": false,
        "auto_keywords": 0,
        "auto_questions": 0,
        "topn_tags": 3,
        "raptor": {
          "use_raptor": false
        },
        "graphrag": {
          "use_graphrag": false
        }
      },
      "source_type": "local",
      "type": "pdf",
      "created_by": "user_id_123",
      "name": "UserGuide_v2.pdf",
      "location": "UserGuide_v2.pdf",
      "size": 102400,
      "token_count": 0,
      "chunk_count": 0,
      "progress": 0.0,
      "progress_msg": "",
      "process_begin_at": null,
      "process_duration": 0.0,
      "meta_fields": {},
      "suffix": "pdf",
      "run": "UNSTART",
      "status": "1",
      "create_time": 1715623400123,
      "create_date": "2024-05-13 10:03:20",
      "update_time": 1715623400123,
      "update_date": "2024-05-13 10:03:20"
    }
  ]
}
```

---

## 2. 获取文档列表 - `list_docs`
**接口描述**: 查询知识库下的文档列表。支持分页检索、关键词搜索、状态筛选等功能。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | **页码**。从 1 开始计数。 |
| page_size | int | 否 | 30 | **每页数量**。 |
| orderby | string | 否 | "create_time" | **排序字段**。支持 `create_time` (创建时间), `name` (文件名), `size` (大小) 等。 |
| desc | boolean | 否 | true | **是否降序**。`true` (最新/最大在前), `false` (最旧/最小在前)。 |
| id | string | 否 | - | **精确筛选 ID**。仅返回指定 ID 的文档。 |
| name | string | 否 | - | **精确筛选文件名**。仅返回指定名称的文档。 |
| keywords | string | 否 | - | **模糊搜索**。匹配文档名称包含该关键词的记录。 |
| suffix | array | 否 | - | **文件后缀筛选** (如 `pdf`, `docx`)。 |
| run | array | 否 | - | **运行状态筛选**。可选值: `UNSTART`, `RUNNING`, `CANCEL`, `DONE`, `FAIL`。 |
| create_time_from | int | 否 | 0 | **起始时间戳** (毫秒)。查询在此时间之后创建的文档。 |
| create_time_to | int | 否 | 0 | **结束时间戳** (毫秒)。查询在此时间之前创建的文档。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 128,
    "docs": [
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003",
        "thumbnail": null,
        "dataset_id": "d1234567890abcdef1234567890abcde",
        "chunk_method": "naive",
        "pipeline_id": null,
        "parser_config": {
          "chunk_token_num": 512,
          "delimiter": "\\n",
          "layout_recognize": "DeepDOC",
          "html4excel": false,
          "auto_keywords": 0,
          "auto_questions": 0,
          "topn_tags": 3,
          "raptor": {
            "use_raptor": false
          },
          "graphrag": {
            "use_graphrag": false
          }
        },
        "source_type": "local",
        "type": "pdf",
        "created_by": "user_id_123",
        "name": "UserGuide_v2.pdf",
        "location": "UserGuide_v2.pdf",
        "size": 102400,
        "token_count": 45000,
        "chunk_count": 120,
        "progress": 1.0,
        "progress_msg": "Parsing finished",
        "process_begin_at": "2024-05-13 10:05:00",
        "process_duration": 45.2,
        "meta_fields": {
            "author": "RAGFlow Team",
            "version": "2.0"
        },
        "suffix": "pdf",
        "run": "DONE",
        "status": "1",
        "create_time": 1715623400123,
        "create_date": "2024-05-13 10:03:20",
        "update_time": 1715623450000,
        "update_date": "2024-05-13 10:05:45"
      }
    ]
  }
}
```

---

## 3. 更新文档信息 - `update_doc`
**接口描述**: 更新文档的名称、状态或解析配置。
**特别注意**: 如果修改了 `chunk_method` 或 `parser_config`，后端会自动将 `run` 状态重置为 `UNSTART`，并清除已有的 chunk 数据，等待重新解析。
**请求方法**: `PUT`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |

#### Body Parameters (JSON)
*(仅需传递要修改的字段)*

| 参数名 | 类型 | 说明 |
|---|---|---|
| name | string | **新文档名称**。需包含文件后缀且不能改变原始文件类型 (如从 `.pdf` 改为 `.txt` 会导致错误)。 |
| enabled | boolean | **启用/禁用**。`true`: 启用 (DEFAULT, 对应 status="1"); `false`: 禁用 (对应 status="0")。禁用后该文档不参与检索。 |
| chunk_method | string | **解析方法**。可选值: `naive`, `manual`, `qa`, `table`, `paper`, `book`, `laws`, `presentation`, `picture`, `one`, `knowledge_graph`, `email`。 |
| parser_config | object | **解析器详细配置**。应与 `chunk_method` 匹配。以下列出 `naive` (通用) 方法的完整配置参数。 |

**parser_config (Naive 模式全量参数)**:
| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| chunk_token_num | int | 512 | **切片最大 Token 数**。 |
| delimiter | string | "\\n" | **分段符**。支持转义字符。 |
| layout_recognize | string | "DeepDOC" | **布局识别模型**。可选 `DeepDOC` 或 `Simple`。 |
| html4excel | boolean | false | **Excel转HTML**。是否将 Excel 解析为 HTML 表格。 |
| auto_keywords | int | 0 | **自动关键词数量**。0 表示不抽取。 |
| auto_questions | int | 0 | **自动问题数量**。0 表示不生成。 |
| topn_tags | int | 3 | **自动标签数量**。 |
| raptor | object | `{ "use_raptor": false }` | **RAPTOR 配置**。设置 `use_raptor: true` 可开启递归摘要索引。 |
| graphrag | object | `{ "use_graphrag": false }` | **GraphRAG 配置**。设置 `use_graphrag: true` 可开启图谱增强。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "e457f92e3c0411ef8d4c0242ac120003",
    "thumbnail": null,
    "dataset_id": "d1234567890abcdef1234567890abcde",
    "chunk_method": "naive",
    "pipeline_id": null,
    "parser_config": {
      "chunk_token_num": 1024,
      "delimiter": "\\n",
      "layout_recognize": "DeepDOC",
      "html4excel": false,
      "auto_keywords": 0,
      "auto_questions": 0,
      "topn_tags": 3,
      "raptor": {
        "use_raptor": false
      },
      "graphrag": {
        "use_graphrag": false
      }
    },
    "source_type": "local",
    "type": "pdf",
    "created_by": "user_id_123",
    "name": "Renamed_Guide.pdf",
    "location": "UserGuide_v2.pdf",
    "size": 102400,
    "token_count": 45000,
    "chunk_count": 0,
    "progress": 0.0,
    "progress_msg": "",
    "process_begin_at": null,
    "process_duration": 0.0,
    "meta_fields": {},
    "suffix": "pdf",
    "run": "UNSTART",
    "status": "0",
    "create_time": 1715623400123,
    "create_date": "2024-05-13 10:03:20",
    "update_time": 1715629999000,
    "update_date": "2024-05-13 12:00:00"
  }
}
```

---

## 4. 删除文档 - `delete`
**接口描述**: 物理删除一个或多个文档。此操作不可恢复，将同时删除数据库记录、MinIO 中的源文件以及 Elasticsearch 中的所有相关切片索引。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array<string> | 是 | **文档 ID 列表**。必须指定要删除的文档 ID。 |

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

## 5. 下载/预览原始文件 - `download`
**接口描述**: 获取文档的原始二进制文件流。响应头将会包含 `Content-Disposition` 字段，指示浏览器以附件形式下载。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/octet-stream`
**Content-Disposition**: `attachment; filename="UserGuide_v2.pdf"`

*(直接返回文件的二进制数据流)*


## 6. 触发/重试文档解析 - `parse`
**接口描述**: 手动触发文档的解析任务。通常在上传文件后、或修改了解析配置（如 `chunk_method`）后调用此接口。支持批量触发。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/chunks`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| document_ids | array<string> | 是 | **文档 ID 列表**。指定需要（重新）解析的文档 ID。 |

**Request Example**:
```json
{
    "document_ids": ["doc_id_1", "doc_id_2"]
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

## 7. 停止文档解析 - `stop_parsing`
**接口描述**: 停止当前正在进行的文档解析任务。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/datasets/<dataset_id>/chunks`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| document_ids | array<string> | 是 | **文档 ID 列表**。指定要停止解析的任务。 |

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

## 8. 获取切片列表 - `list_chunks`
**接口描述**: 获取指定文档已解析出的切片（Chunk）列表。支持分页和关键词搜索。返回结果包含文档的详细元数据和具体的切片内容。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | **页码**。 |
| page_size | int | 否 | 30 | **每页数量**。 |
| keywords | string | 否 | - | **搜索关键词**。在切片内容中进行全文检索。 |
| id | string | 否 | - | **精确切片 ID**。若指定，则只返回该 ID 对应的切片。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 150,
    "chunks": [
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003_0",
        "content": "RAGFlow 是一款基于深度文档理解的开源 RAG（检索增强生成）引擎。它旨在为各种规模的企业提供精简的 RAG 工作流。RAGFlow 结合了传统文档处理的稳健性与现代大语言模型（LLM）的生成能力，确保在处理复杂格式数据（如 PDF 表格、扫描件等）时依然能保持极高的召回率和准确性。",
        "document_id": "doc_uuid_123",
        "docnm_kwd": "RAGFlow_UserGuide_v2.pdf",
        "important_keywords": ["RAGFlow", "开源", "深度文档理解", "LLM"],
        "questions": ["什么是 RAGFlow?", "RAGFlow 的主要特点是什么?"],
        "image_id": "",
        "dataset_id": "kb_uuid_456",
        "available": true,
        "positions": [1]
      },
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003_1",
        "content": "主要特性：\n1. **深度文档解析**：内置 DeepDOC 识别引擎，精准还原表格、段落结构。\n2. **多路召回**：支持关键词 + 向量的混合检索。\n3. **可视化编排**：提供基于 Graph 的工作流编排能力。",
        "document_id": "doc_uuid_123",
        "docnm_kwd": "RAGFlow_UserGuide_v2.pdf",
        "important_keywords": ["DeepDOC", "混合检索", "可视化编排"],
        "questions": [],
        "image_id": "img_uuid_789",
        "dataset_id": "kb_uuid_456",
        "available": true,
        "positions": [2]
      }
    ],
    "doc": {
        "id": "doc_uuid_123",
        "name": "RAGFlow_UserGuide_v2.pdf",
        "chunk_count": 150,
        "token_count": 45000,
        "chunk_method": "naive",
        "run": "DONE",
        "status": "1",
        "progress": 1.0,
        "progress_msg": "Parsing finished",
        "process_begin_at": "2024-05-13 10:05:00",
        "process_duration": 45.2,
        "meta_fields": {
             "author": "RAGFlow Team",
             "version": "2.0"
        },
        "create_time": 1715623400123,
        "create_date": "2024-05-13 10:03:20",
        "update_time": 1715623450000,
        "update_date": "2024-05-13 10:05:45",
        "dataset_id": "kb_uuid_456"
    }
  }
}
```

---

## 9. 手动新增切片 - `add_chunk`
**接口描述**: 向指定文档中手动添加一个新的切片。系统会自动计算该切片的向量嵌入 (Embedding)。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| content | string | 是 | **切片内容**。手动输入的文本内容。 |
| important_keywords | array<string> | 否 | **重要关键词**。用于关键词检索增强。 |
| questions | array<string> | 否 | **预设问题**。用于 Q&A 检索模式增强。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "chunk": {
        "id": "new_chunk_uuid_999",
        "content": "这是管理员手动添加的一条补充切片，用于修正文档中缺失的关键信息。",
        "document_id": "doc_uuid_123",
        "docnm_kwd": "RAGFlow_UserGuide_v2.pdf",
        "important_keywords": ["手动添加", "补充信息"],
        "questions": ["如何手动添加切片?"],
        "image_id": "",
        "dataset_id": "kb_uuid_456",
        "available": true,
        "positions": []
    }
  }
}
```

---

## 10. 修改切片信息 - `update_chunk`
**接口描述**: 修改已存在的切片内容、关键词、可用状态等。修改内容后，系统会自动重新计算向量。
**请求方法**: `PUT`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks/<chunk_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |
| chunk_id | string | 是 | **切片 ID**。 |

#### Body Parameters (JSON)
*(以下字段均为可选，仅传递需修改的字段)*

| 参数名 | 类型 | 说明 |
|---|---|---|
| content | string | **新的切片内容**。 |
| important_keywords | array<string> | **更新关键词列表**。覆盖原有列表。 |
| available | boolean | **启用/禁用**。`true`: 启用 (默认); `false`: 禁用 (检索时将忽略此切片)。 |

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

## 11. 删除切片 - `rm_chunk`
**接口描述**: 批量删除文档中的指定切片。
**请求方法**: `DELETE`
**接口地址**: `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |
| document_id | string | 是 | **文档 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chunk_ids | array<string> | 是 | **切片 ID 列表**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "deleted 2 chunks",
  "data": null
}
```


## 12. 获取元数据摘要 - `metadata_summary`
**接口描述**: 获取知识库中所有文档的元数据摘要信息。通常用于前端展示知识库的数据分布概况，例如不同文件类型的数量统计、文件状态分布等。
**请求方法**: `GET`
**接口地址**: `/api/v1/datasets/<dataset_id>/metadata/summary`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Query Parameters
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "summary": {
      "total_doc_count": 120,
      "total_token_count": 500000,
      "file_type_distribution": {
        "pdf": 80,
        "docx": 30,
        "txt": 10
      },
      "status_distribution": {
        "1": 118, // 正常启用
        "0": 2    // 禁用
      },
      "custom_metadata": {
        "author": {
            "Alice": 50,
            "Bob": 30
        },
        "department": {
            "HR": 20,
            "Engineering": 100
        }
      }
    }
  }
}
```

---

## 13. 批量更新元数据 - `metadata_batch_update`
**接口描述**: 对知识库中的文档进行批量元数据修改。支持基于复杂的条件筛选文档，然后执行批量更新或删除元数据字段的操作。
**请求方法**: `POST`
**接口地址**: `/api/v1/datasets/<dataset_id>/metadata/update`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| dataset_id | string | 是 | **知识库 ID**。 |

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| selector | object | 否 | **筛选器**。定义要更新哪些文档。如果不传，可能作用于全量文档（请谨慎）。 |
| updates | array | 否 | **更新操作列表**。包含 `key` 和 `value`。 |
| deletes | array | 否 | **删除操作列表**。包含 `key`。 |

**Request Example (复杂场景)**:
```json
{
  "selector": {
    "document_ids": ["doc_id_101", "doc_id_102"],
    "metadata_condition": {
       "logic": "and",
       "conditions": [
          {"key": "author", "value": "OldName", "operator": "eq"},
          {"key": "status", "value": "draft", "operator": "eq"}
       ]
    }
  },
  "updates": [
    {"key": "author", "value": "Admin"},
    {"key": "reviewed_by", "value": "ManagerA"}
  ],
  "deletes": [
    {"key": "temp_tag"},
    {"key": "draft_flag"}
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
    "updated": 2,        // 实际更新成功的文档数量
    "matched_docs": 2    // 匹配到的文档数量
  }
}
```

---

## 14. 检索测试 (Hit Test) - `retrieval_test`
**接口描述**: 在指定的知识库中进行模拟检索测试。此接口用于验证分段（Chunk）质量、检索参数（相似度阈值、Top K）的效果，是调试 RAG 效果的核心工具。
**请求方法**: `POST`
**接口地址**: `/api/v1/retrieval`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`
**注意**: 即使是简单的查询，由于包含较多配置参数，本接口也设计为 `POST` 请求。

### 请求参数 (Request)
#### Path Parameters
无

#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| dataset_ids | array<string> | 是 | - | **目标知识库 ID 列表**。支持跨多个知识库检索。 |
| question | string | 是 | - | **用户查询问题**。 |
| similarity_threshold | float | 否 | 0.2 | **相似度阈值**。低于此分数的 Chunk 将被过滤。 |
| vector_similarity_weight | float | 否 | 0.3 | **向量权重**。混合检索时，向量检索结果的权重 (0~1)。剩余权重归于关键词检索。 |
| top_k | int | 否 | 1024 | **初筛数量**。向量检索返回的候选切片数量。 |
| rerank_id | string | 否 | - | **重排模型 ID**。若指定，将对检索结果进行 Rerank 二次排序。 |
| highlight | boolean | 否 | true | **高亮匹配**。是否在返回内容中高亮关键词。 |
| keyword | boolean | 否 | false | **关键词增强**。是否使用 LLM 提取问题关键词以增强检索。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 15,
    "chunks": [
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003_12",
        "content": "RAGFlow 支持多种文档解析模式，其中 DeepDOC 模式特别适合处理包含大量表格和扫描件的 PDF 文档。它使用深度学习模型识别文档布局，精准提取表格内容。",
        "document_id": "doc_uuid_123",
        "dataset_id": "kb_uuid_456",
        "document_name": "RAGFlow_UserGuide_v2.pdf",
        "document_keyword": "RAGFlow_UserGuide_v2.pdf",
        "similarity": 0.88,
        "vector_similarity": 0.85,
        "term_similarity": 0.92,
        "index": 12,
        "highlight": "RAGFlow 支持多种<em>文档解析模式</em>，其中 <em>DeepDOC</em> 模式特别适合处理包含大量表格和扫描件的 PDF 文档。",
        "important_keywords": ["DeepDOC", "PDF"],
        "questions": ["DeepDOC 模式有什么用?"],
        "image_id": "",
        "positions": [12]
      },
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003_15",
        "content": "如果文档主要由纯文本构成，建议使用 Naive 模式。该模式解析速度快，适合通用场景。",
        "document_id": "doc_uuid_123",
        "dataset_id": "kb_uuid_456",
        "document_name": "RAGFlow_UserGuide_v2.pdf",
        "document_keyword": "RAGFlow_UserGuide_v2.pdf",
        "similarity": 0.45,
        "vector_similarity": 0.40,
        "term_similarity": 0.50,
        "index": 15,
        "highlight": "如果文档主要由纯文本构成，建议使用 <em>Naive</em> 模式。",
        "important_keywords": ["Naive", "纯文本"],
        "questions": [],
        "image_id": "",
        "positions": [15]
      }
    ],
    "doc_aggs": [
        {
            "doc_name": "RAGFlow_UserGuide_v2.pdf",
            "doc_id": "doc_uuid_123",
            "count": 2
        }
    ]
  }
}
```
