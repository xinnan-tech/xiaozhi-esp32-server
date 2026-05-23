# 全模块服务端上线与配置迁移说明

本文面向已经运行过 `xiaozhi-server` Python 服务，并准备补齐智控台、数据库和缓存的部署场景。它是 [全模块安装文档](./Deployment_all.md) 的补充，重点说明如何在不破坏既有 `data/.config.yaml` 和设备使用链路的前提下，把配置迁移到 Web 管理后台。

## 模块职责

| 模块 | 默认端口 | 作用 | 是否必须持久化 |
| --- | --- | --- | --- |
| `xiaozhi-esp32-server` | `8000`, `8003` | Python 设备服务，负责 WebSocket、语音链路、LLM/TTS/ASR 调用、视觉 HTTP 接口 | `data/`, `models/` |
| `xiaozhi-esp32-server-web` | `8002` | Java `manager-api` + Vue 管理后台，负责用户、设备、智能体、模型、OTA 管理 | `uploadfile/` |
| `xiaozhi-esp32-server-db` | 容器内 `3306` | MySQL 8，保存用户、设备、智能体、模型配置、聊天历史等 | `mysql/data/` |
| `xiaozhi-esp32-server-redis` | 容器内 `6379` | Redis 8，保存登录态、缓存、临时状态 | 通常不需要 |

全模块部署后，设备仍然连接 Python 服务；Python 服务通过 `manager-api` 读取设备绑定、智能体和模型配置。

## 不影响现有服务的原则

1. 先备份原有 `data/.config.yaml`，不要直接覆盖。建议同时备份 `data/`、`models/`、`uploadfile/`、`mysql/data/`。
2. 先启动 `manager-api`、MySQL、Redis，并完成管理员初始化，再让 Python 服务切换到 `manager-api` 配置源。
3. `8000` 是设备 WebSocket，`8002` 是管理后台和 OTA，`8003` 是 Python HTTP 能力。公网只暴露必要入口，MySQL 和 Redis 不要暴露到公网。
4. 如果已有 Nginx、Caddy 或其他网站在使用 `80/443`，不要让 Docker 直接占用这两个端口。应通过反向代理按路径转发到 `8000/8002`。
5. 切换前先保留文件配置中的 Gemini、OpenAI/ChatGPT、TTS、ASR、prompt 等字段；确认后台配置完整后再重启 Python 服务。

## 从文件配置迁移到智控台

### 1. 启动全模块依赖

按 [Deployment_all.md](./Deployment_all.md) 启动：

```bash
docker compose -f docker-compose_all.yml up -d
docker compose -f docker-compose_all.yml ps
```

确认四个容器都正常：

```bash
docker logs --tail=100 xiaozhi-esp32-server-web
docker logs --tail=100 xiaozhi-esp32-server
```

### 2. 初始化管理员

浏览器打开 `http://127.0.0.1:8002` 或你的反向代理地址，注册第一个账号。第一个账号会成为超级管理员，后续账号默认是普通用户。

不要把默认账号密码写入公开文档或仓库。生产环境应改成强密码，并限制管理后台公网访问范围。

### 3. 写入 `manager-api` 连接信息

在智控台进入 `参数管理`，找到 `server.secret`，复制参数值。

将 `main/xiaozhi-server/config_from_api.yaml` 复制为运行目录的 `data/.config.yaml`，然后填写：

```yaml
server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003
  vision_explain: http://你的内网IP或域名:8003/mcp/vision/explain

manager-api:
  url: http://xiaozhi-esp32-server-web:8002/xiaozhi
  secret: 这里填写智控台里的server.secret

prompt_template: agent-base-prompt.txt
```

Docker 全模块部署时，`manager-api.url` 推荐使用容器名 `http://xiaozhi-esp32-server-web:8002/xiaozhi`，不要写 `127.0.0.1`。源码本地运行时，才使用 `http://127.0.0.1:8002/xiaozhi`。

### 4. 迁移系统入口地址

在智控台的 `参数管理` 中配置：

| 参数 | 内网示例 | 公网 HTTPS 示例 |
| --- | --- | --- |
| `server.websocket` | `ws://192.168.1.10:8000/xiaozhi/v1/` | `wss://example.com/xiaozhi/v1/` |
| `server.ota` | `http://192.168.1.10:8002/xiaozhi/ota/` | `https://example.com/xiaozhi/ota/` |

公网 HTTPS 场景下，常见反向代理规则是：

| 路径 | 转发目标 |
| --- | --- |
| `/xiaozhi/v1/` | Python 服务 `127.0.0.1:8000`，需要支持 WebSocket Upgrade |
| `/xiaozhi/ota/` | 管理后台 `127.0.0.1:8002` |
| 管理后台路径 | 管理后台 `127.0.0.1:8002`，建议使用不易猜测的路径前缀或额外鉴权 |

### 5. 迁移 Gemini 和 OpenAI/ChatGPT 配置

Python 服务的 LLM 加载逻辑按配置里的 `type` 选择 provider。迁移到智控台后，模型配置中的 `config_json` 仍要保留这些关键字段。

Gemini 示例：

```json
{
  "type": "gemini",
  "api_key": "你的Gemini API密钥",
  "model_name": "你的Gemini模型",
  "http_proxy": "",
  "https_proxy": "",
  "thinking_budget": 0
}
```

OpenAI/ChatGPT 或 OpenAI 兼容接口示例：

```json
{
  "type": "openai",
  "base_url": "https://api.openai.com/v1",
  "model_name": "你的ChatGPT模型",
  "api_key": "你的OpenAI API密钥",
  "temperature": 0.7,
  "max_tokens": 800,
  "top_p": 0.9
}
```

注意事项：

1. `type: "openai"` 代表走 OpenAI 兼容 provider，不只限 OpenAI 官方服务。智谱、豆包、月之暗面、LM Studio 等兼容接口也复用这条链路。
2. `base_url` 和旧配置里的 `url` 容易混用。当前 Python provider 优先读取 `base_url`，没有时才读取 `url`。迁移时建议统一填 `base_url`。
3. 如果原来同时支持 Gemini 和 ChatGPT，后台里应保留两条 LLM 配置；智能体的 `大语言模型` 只选择当前要使用的那一条。
4. Gemini 的 `thinking_budget` 建议显式写入。语音助手追求首字延迟时通常填 `0`，避免默认思考模式拉长响应。

### 6. 迁移智能体

在智控台进入 `智能体管理`：

1. 新建或编辑智能体。
2. 将旧 `prompt` 或 `.agent-base-prompt.txt` 中的角色设定迁移到智能体角色配置。
3. 逐项选择 ASR、VAD、LLM、TTS、Memory、Intent。
4. 如果使用工具调用，确认 `Intent` 选择支持函数调用的配置，并迁移原来的 `plugins` 或 MCP 配置。
5. 保存后重启 Python 服务，让设备连接时读取新的智能体配置。

原 `agent-base-prompt.txt` 是模板，不等同于某个智能体的人设。模板里的 `{{base_prompt}}`、`{{language}}`、`{{weather_info}}`、`{{dynamic_context}}` 等占位符应继续保留；具体人设放到智能体的角色设定里。

### 7. 绑定设备

设备首次连接全模块服务端时，如果没有绑定，会进入激活/绑定流程。绑定后，`manager-api` 会通过设备 MAC 找到默认智能体。

排查顺序：

1. 在 `设备管理` 中确认设备 MAC 是否存在。
2. 确认设备已绑定到正确用户。
3. 确认设备关联了正确智能体。
4. 查看 Python 服务日志，确认设备连接后没有回退到本地文件配置。

## 功能对应关系

| 功能 | 依赖模块 | 迁移时检查点 |
| --- | --- | --- |
| Web 管理 UI | `xiaozhi-esp32-server-web` | `8002` 或反向代理可访问 |
| 历史对话查看 | MySQL + 智能体上报配置 | 智能体保存后，聊天历史表应有数据 |
| 多设备分组 | MySQL 设备表和绑定关系 | 每台设备 MAC 应绑定到正确智能体 |
| 多智能体切换 | 智能体管理 | 设备默认智能体、用户权限正确 |
| 用户账号 | 管理后台 | 第一个账号为管理员，后续账号权限不同 |
| OTA 固件管理 | `server.ota` + 管理后台 | 设备 OTA 地址指向 `manager-api` |
| 使用统计/监控 | MySQL + 管理后台 | 确认聊天和设备事件可写入数据库 |
| 声纹识别 | 声纹服务 URL + 智能体配置 | 未配置声纹服务时不会生效 |

## 验证清单

迁移完成后，至少检查以下项目：

```bash
docker compose -f docker-compose_all.yml ps
docker logs --tail=100 xiaozhi-esp32-server-web
docker logs --tail=100 xiaozhi-esp32-server
```

浏览器检查：

1. 管理后台能登录。
2. `参数管理` 中 `server.websocket` 和 `server.ota` 是设备实际可访问地址。
3. `模型配置` 中 Gemini 和 OpenAI/ChatGPT 配置都存在，且密钥没有丢。
4. `智能体管理` 中能看到目标智能体，且选择了正确的 LLM/TTS/ASR。
5. `设备管理` 中能看到目标设备，并绑定到正确智能体。

设备侧检查：

1. OTA 接口返回包含 `websocket.url` 的 JSON。
2. 设备能连上 `ws://.../xiaozhi/v1/` 或 `wss://.../xiaozhi/v1/`。
3. 语音问答能调用后台选择的 LLM。
4. 在管理后台能看到设备状态或聊天记录。

## 常见问题

### 管理后台打开是空的

通常是没有创建智能体，或当前登录用户不是设备/智能体所属用户。用管理员账号检查 `智能体管理`、`设备管理`、用户权限和设备绑定关系。

### Python 服务仍然读旧配置

检查运行目录的 `data/.config.yaml` 是否包含 `manager-api.url` 和正确的 `manager-api.secret`。修改后需要重启 `xiaozhi-esp32-server`。

### Gemini 能用，ChatGPT 丢了

检查后台是否只迁移了 `LLM_GeminiLLM`。ChatGPT/OpenAI 应作为独立 LLM 配置保留，`config_json.type` 填 `openai`，并填入 `base_url`、`model_name`、`api_key`。

### 公网 HTTPS 能打开后台，但设备连不上

设备 WebSocket 需要反向代理支持 Upgrade 头。确认 `/xiaozhi/v1/` 转发到 Python 的 `8000`，而不是转发到管理后台的 `8002`。

### OTA 接口返回错误地址

检查 `参数管理` 的 `server.ota` 和 `server.websocket`。全模块部署时 OTA 通常由 `manager-api` 提供，WebSocket 由 Python 服务提供，两者不是同一个上游端口。
