# RAGFlow 文件管理接口详解 (File Management API)

## 1. 上传文件 - `upload`
**接口描述**: 上传一个或多个文件到指定文件夹。支持多文件上传 (Multipart)。上传成功后，文件将存储在 MinIO/S3 中，并返回文件元数据列表。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/upload`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`
**Content-Type**: `multipart/form-data`

### 请求参数 (Request)
#### Form Data Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | file | 是 | **文件二进制流**。支持多文件上传。 |
| parent_id | string | 否 | **父级目录 ID**。如果省略，默认上传到根目录 (root)。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "e457f92e3c0411ef8d4c0242ac120003",
      "parent_id": "root_folder_id_123",
      "tenant_id": "tenant_uuid_456",
      "created_by": "user_uuid_789",
      "type": "pdf",
      "name": "ProjectReport.pdf",
      "location": "ProjectReport.pdf",
      "size": 204800,
      "source_type": "",
      "create_time": 1715623400123,
      "create_date": "2024-05-13 10:03:20",
      "update_time": 1715623400123,
      "update_date": "2024-05-13 10:03:20"
    }
  ]
}
```

---

## 2. 新建文件夹 - `create`
**接口描述**: 在指定父目录下创建一个新的文件夹（逻辑目录）。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/create`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | **文件夹名称**。同一目录下不可重名。 |
| parent_id | string | 否 | **父级目录 ID**。省略则默认为根目录。 |
| type | string | 是 | **类型**。固定值为 `FOLDER` 创建文件夹。 |

**Request Example**:
```json
{
  "name": "Year2024_Reports",
  "parent_id": "root_folder_id_123",
  "type": "FOLDER"
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "folder_uuid_abc",
    "parent_id": "root_folder_id_123",
    "tenant_id": "tenant_uuid_456",
    "created_by": "user_uuid_789",
    "name": "Year2024_Reports",
    "location": "",
    "size": 0,
    "type": "folder",
    "source_type": "",
    "create_time": 1715623500000,
    "create_date": "2024-05-13 10:05:00",
    "update_time": 1715623500000,
    "update_date": "2024-05-13 10:05:00"
  }
}
```

---

## 3. 获取文件列表 - `list_files`
**接口描述**: 分页获取指定文件夹下的文件和子文件夹列表。支持按名称模糊搜索。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/list`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| parent_id | string | 否 | (Root) | **父级目录 ID**。指定要查看的目录 ID。 |
| keywords | string | 否 | - | **搜索关键词**。按文件名模糊搜索。 |
| page | int | 否 | 1 | **页码**。 |
| page_size | int | 否 | 15 | **每页数量**。 |
| orderby | string | 否 | "create_time" | **排序字段**。 |
| desc | boolean | 否 | true | **是否降序**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 25,
    "parent_folder": {
      "id": "root_folder_id_123",
      "parent_id": "",
      "tenant_id": "tenant_uuid_456",
      "created_by": "system",
      "name": "ROOT",
      "location": "",
      "size": 0,
      "type": "folder",
      "source_type": "",
      "create_time": 1710000000000,
      "create_date": "2024-03-01 00:00:00",
      "update_time": 1710000000000,
      "update_date": "2024-03-01 00:00:00"
    },
    "files": [
      {
        "id": "folder_uuid_abc",
        "parent_id": "root_folder_id_123",
        "tenant_id": "tenant_uuid_456",
        "created_by": "user_uuid_789",
        "name": "Year2024_Reports",
        "location": "",
        "size": 0,
        "type": "folder",
        "source_type": "",
        "create_time": 1715623500000,
        "create_date": "2024-05-13 10:05:00",
        "update_time": 1715623500000,
        "update_date": "2024-05-13 10:05:00"
      },
      {
        "id": "e457f92e3c0411ef8d4c0242ac120003",
        "parent_id": "root_folder_id_123",
        "tenant_id": "tenant_uuid_456",
        "created_by": "user_uuid_789",
        "name": "ProjectReport.pdf",
        "location": "ProjectReport.pdf",
        "size": 204800,
        "type": "pdf",
        "source_type": "",
        "create_time": 1715623400123,
        "create_date": "2024-05-13 10:03:20",
        "update_time": 1715623400123,
        "update_date": "2024-05-13 10:03:20"
      }
    ]
  }
}
```

---

## 4. 获取文件流 (下载) - `get`
**接口描述**: 通过文件 ID 下载文件内容。不同于获取元数据，该接口直接返回文件的二进制流（Octet-stream 或 Image 等）。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/get/<file_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_id | string | 是 | **文件 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/octet-stream` (或具体 MIME 类型如 `image/png`)

*(返回二进制文件流)*

---

## 5. 下载附件 - `download_attachment`
**接口描述**: 这是一个通用的附件下载接口，通常用于系统内部引用或特定路径的下载。它使用 `attachment_id`（通常对应 MinIO 中的存储路径/Key）来检索文件。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/download/<attachment_id>`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Path Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| attachment_id | string | 是 | **附件 ID / 存储 Key**。通常对应底层存储的唯一标识符。 |

#### Query Parameters
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| ext | string | 否 | "markdown" | **文件扩展名**。用于设置响应头中的 Content-Type。 |

### 响应参数 (Response)
**Content-Type**: `application/octet-stream` (或根据 ext 参数推断)

*(返回二进制文件流)*


## 6. 重命名文件/文件夹 - `rename`
**接口描述**: 修改文件或文件夹的名称。对于文件，通常不允许修改扩展名（后缀）。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/rename`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_id | string | 是 | **目标文件/文件夹 ID**。 |
| name | string | 是 | **新名称**。需符合文件命名规范，且同一目录下不可重名。 |

**Request Example**:
```json
{
  "file_id": "file_uuid_123",
  "name": "New_Report_Final.pdf"
}
```

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

## 7. 移动文件/文件夹 - `move`
**接口描述**: 批量移动文件或文件夹到指定的目录 (Move)。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/mv`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| src_file_ids | array<string> | 是 | **源文件/文件夹 ID 列表**。支持批量移动。 |
| dest_file_id | string | 是 | **目标文件夹 ID**。必须是已存在的文件夹 ID。 |

**Request Example**:
```json
{
  "src_file_ids": ["file_id_1", "file_id_2"],
  "dest_file_id": "folder_id_target"
}
```

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

## 8. 删除文件/文件夹 - `rm`
**接口描述**: 批量删除文件或文件夹。如果是文件夹，将递归删除其下的所有内容。此操作不可恢复。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/rm`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_ids | array<string> | 是 | **待删除的文件/文件夹 ID 列表**。 |

**Request Example**:
```json
{
  "file_ids": ["file_uuid_to_delete_1", "folder_uuid_to_delete_2"]
}
```

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

## 9. 文件转知识库文档 - `convert`
**接口描述**: 将已上传的文件（File）导入到指定的知识库（Dataset）中，转换为文档（Document）并进行解析。这是一个“文件 -> 知识库”的桥接操作。
**请求方法**: `POST`
**接口地址**: `/api/v1/file/convert`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Body Parameters (JSON)
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_ids | array<string> | 是 | **源文件 ID 列表**。必须是已存在于文件管理系统中的 ID。 |
| kb_ids | array<string> | 是 | **目标知识库 ID 列表**。文件将被同时导入到这些知识库中。 |

**Request Example**:
```json
{
  "file_ids": ["file_uuid_pdf_1", "file_uuid_txt_2"],
  "kb_ids": ["dataset_uuid_A"]
}
```

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "mapping_uuid_1",
      "file_id": "file_uuid_pdf_1",
      "document_id": "doc_uuid_created_in_kb_A",
      "create_time": 1715623600123,
      "create_date": "2024-05-13 10:06:40",
      "update_time": 1715623600123,
      "update_date": "2024-05-13 10:06:40"
    },
    {
      "id": "mapping_uuid_2",
      "file_id": "file_uuid_txt_2",
      "document_id": "doc_uuid_created_in_kb_A",
      "create_time": 1715623600124,
      "create_date": "2024-05-13 10:06:40",
      "update_time": 1715623600124,
      "update_date": "2024-05-13 10:06:40"
    }
  ]
}
```


## 10. 获取根目录信息 - `get_root_folder`
**接口描述**: 获取当前用户的根目录文件夹信息。每个用户（Tenant）都有且仅有一个系统自动创建的根目录。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/root_folder`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Query Parameters
无

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "root_folder": {
      "id": "root_folder_id_123",
      "parent_id": "",
      "tenant_id": "tenant_uuid_456",
      "created_by": "system",
      "name": "ROOT",
      "location": "",
      "size": 0,
      "type": "folder",
      "source_type": "",
      "create_time": 1710000000000,
      "create_date": "2024-03-01 00:00:00",
      "update_time": 1710000000000,
      "update_date": "2024-03-01 00:00:00"
    }
  }
}
```

---

## 11. 获取父目录信息 - `get_parent_folder`
**接口描述**: 获取指定文件或文件夹的直接父级目录信息。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/parent_folder`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Query Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_id | string | 是 | **当前文件/文件夹 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "parent_folder": {
      "id": "root_folder_id_123",
      "parent_id": "",
      "tenant_id": "tenant_uuid_456",
      "created_by": "system",
      "name": "ROOT",
      "location": "",
      "size": 0,
      "type": "folder",
      "source_type": "",
      "create_time": 1710000000000,
      "create_date": "2024-03-01 00:00:00",
      "update_time": 1710000000000,
      "update_date": "2024-03-01 00:00:00"
    }
  }
}
```

---

## 12. 获取完整路径 (面包屑) - `get_all_parent_folders`
**接口描述**: 获取指定文件或文件夹的所有上级目录列表，形成完整的路径链。返回的列表顺序通常是从根目录到直接父目录（有序）。此接口常用于前端展示“面包屑导航” (Breadcrumbs)。
**请求方法**: `GET`
**接口地址**: `/api/v1/file/all_parent_folder`
**鉴权方式**: Header `Authorization: Bearer <API_KEY>`

### 请求参数 (Request)
#### Query Parameters
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_id | string | 是 | **目标文件/文件夹 ID**。 |

### 响应参数 (Response)
**Content-Type**: `application/json`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "parent_folders": [
      {
        "id": "root_folder_id_123",
        "parent_id": "",
        "tenant_id": "tenant_uuid_456",
        "created_by": "system",
        "name": "ROOT",
        "location": "",
        "size": 0,
        "type": "folder",
        "source_type": "",
        "create_time": 1710000000000,
        "create_date": "2024-03-01 00:00:00",
        "update_time": 1710000000000,
        "update_date": "2024-03-01 00:00:00"
      },
      {
         "id": "folder_project_a_id",
         "parent_id": "root_folder_id_123",
         "tenant_id": "tenant_uuid_456",
         "created_by": "user_id_001",
         "name": "Project A Docs",
         "location": "",
         "size": 0,
         "type": "folder",
         "source_type": "",
         "create_time": 1715000000000,
         "create_date": "2024-05-01 09:00:00",
         "update_time": 1715000000000,
         "update_date": "2024-05-01 09:00:00"
      }
    ]
  }
}
```
