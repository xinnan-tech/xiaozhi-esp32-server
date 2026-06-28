# 反馈系统后端 (Feedback Backend)

客户反馈系统独立后端服务，基于 **FastAPI + DDD 架构**，与 xiaozhi-server 完全解耦。

## 架构

```
feedback-backend/
├── app/
│   ├── domain/                    ← DDD 领域层
│   │   ├── store/                 (门店: Entity/VO/Repository接口)
│   │   ├── employee/              (员工: Entity/VO/Repository接口)
│   │   ├── feedback/              (反馈记录: Entity/VO/Repository接口)
│   │   └── agent/                 (智能体配置: Entity/VO/Repository接口)
│   ├── application/               ← 应用层 (用例服务)
│   │   ├── feedback_service.py    (AI 反馈处理: 3步 LLM Pipeline)
│   │   ├── stats_service.py       (统计分析)
│   │   ├── store_service.py       (门店 CRUD)
│   │   ├── employee_service.py    (员工 CRUD)
│   │   └── agent_config_service.py(智能体配置)
│   ├── infrastructure/            ← 基础设施层
│   │   ├── persistence/           (MySQL ORM + Repository 实现)
│   │   ├── llm/                   (LLM 调用服务)
│   │   └── xiaozhi/               (xiaozhi-server 客户端)
│   ├── interfaces/                ← 接口层 (MVC Controller)
│   │   └── api/                   (REST API: /api/v1/*)
│   └── shared/                    ← 共享: config/exceptions/utils
├── prompts/                       ← 提示词模板
├── admin-ui/                      ← 后台管理前端 (Phase C)
├── migrations/                    ← Alembic 数据库迁移
├── config.yaml                    ← 配置文件
├── alembic.ini                    ← Alembic 配置
├── requirements.txt
├── start.py                       ← 启动脚本
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd main/feedback-backend
pip install -r requirements.txt
```

### 2. 创建数据库

```sql
CREATE DATABASE feedback_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

### 3. 修改配置

编辑 `config.yaml`，修改数据库连接信息和 LLM API Key：

```yaml
database:
  host: "127.0.0.1"
  port: 3306
  username: "root"
  password: "你的密码"
  database: "feedback_db"

llm:
  provider: "openai"
  openai:
    api_key: "你的API Key"
```

### 4. 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "init tables"

# 执行迁移
alembic upgrade head
```

> 开发模式下，首次启动会自动创建表，可以跳过 Alembic。

### 5. 启动服务

```bash
python start.py
```

访问：
- API 文档: http://localhost:8009/docs
- 后台管理: http://localhost:8009/admin
- 健康检查: http://localhost:8009/health

### 默认管理员

- 用户名: `admin`
- 密码: `admin123`

> ⚠️ 首次登录后请立即修改密码！

## API 接口

### 公开接口（无需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/public/store/{storeCode}` | 根据编码获取门店 |
| GET | `/api/v1/public/employees/{storeId}` | 获取门店员工列表 |
| POST | `/api/v1/public/process` | AI 处理反馈 |
| POST | `/api/v1/public/record` | 保存反馈记录 |
| POST | `/api/v1/public/device-init` | 设备初始化 |

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 管理员登录 |
| GET | `/api/v1/auth/me` | 获取当前用户 |

### 管理接口（需要认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/store/list` | 门店列表 |
| POST | `/api/v1/store` | 创建门店 |
| PUT | `/api/v1/store/{id}` | 更新门店 |
| POST | `/api/v1/store/delete` | 删除门店 |
| GET | `/api/v1/employee/list` | 员工列表 |
| POST | `/api/v1/employee` | 创建员工 |
| PUT | `/api/v1/employee/{id}` | 更新员工 |
| POST | `/api/v1/employee/delete` | 删除员工 |
| GET | `/api/v1/record/list` | 反馈记录列表 |
| GET | `/api/v1/stats/overview` | 统计概览 |
| GET | `/api/v1/stats/daily` | 按天统计 |
| GET | `/api/v1/stats/by-store` | 按门店统计 |
| GET | `/api/v1/agent-config/list` | 智能体配置列表 |
| POST | `/api/v1/agent-config` | 创建智能体配置 |
| PUT | `/api/v1/agent-config/{id}` | 更新智能体配置 |

## Docker 部署

在 `docker-compose_all.yml` 中添加：

```yaml
feedback-backend:
  build:
    context: .
    dockerfile: Dockerfile-feedback
  ports:
    - "8009:8009"
  environment:
    FEEDBACK_DB_HOST: xiaozhi-esp32-server-db
    FEEDBACK_DB_PASSWORD: "123456"
    FEEDBACK_LLM_API_KEY: "your-api-key"
  depends_on:
    - xiaozhi-esp32-server-db
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| FEEDBACK_DB_HOST | 数据库主机 | 127.0.0.1 |
| FEEDBACK_DB_PORT | 数据库端口 | 3306 |
| FEEDBACK_DB_USER | 数据库用户 | root |
| FEEDBACK_DB_PASSWORD | 数据库密码 | 123456 |
| FEEDBACK_DB_NAME | 数据库名 | feedback_db |
| FEEDBACK_SERVER_HOST | 服务监听地址 | 0.0.0.0 |
| FEEDBACK_SERVER_PORT | 服务端口 | 8009 |
| FEEDBACK_LLM_PROVIDER | LLM 提供商 | openai |
| FEEDBACK_LLM_API_KEY | LLM API Key | - |
| FEEDBACK_LLM_BASE_URL | LLM API Base URL | - |
| FEEDBACK_LLM_MODEL | LLM 模型 | gpt-4o-mini |
| FEEDBACK_AUTH_SECRET | JWT 密钥 | (内置) |
| FEEDBACK_ADMIN_USER | 管理员用户名 | admin |
| FEEDBACK_ADMIN_PASSWORD | 管理员密码 | admin123 |
| FEEDBACK_XIAOZHI_WS_URL | xiaozhi WebSocket URL | ws://127.0.0.1:18000 |
| FEEDBACK_XIAOZHI_HTTP_URL | xiaozhi HTTP URL | http://127.0.0.1:18003 |

## 数据库表

| 表名 | 说明 |
|------|------|
| feedback_store | 门店信息 |
| feedback_employee | 员工信息 |
| feedback_record | 反馈记录（含满意度） |
| agent_config | 智能体配置（对话轮次/提示词/LLM） |
| admin_user | 管理员用户 |

## 技术栈

- **Web 框架**: FastAPI 0.115
- **ORM**: SQLAlchemy 2.0
- **数据库**: MySQL (独立数据库 feedback_db)
- **迁移**: Alembic
- **LLM**: OpenAI SDK (兼容 OpenAI 协议)
- **认证**: JWT (python-jose + passlib)
- **日志**: loguru
