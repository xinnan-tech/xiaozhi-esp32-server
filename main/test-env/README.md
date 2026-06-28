# CRM + 反馈系统本机测试环境

这个目录用于在当前 Windows 主机上启动一套**独立于现有生产容器**的测试环境。

当前生产环境仍使用：

- Compose：`../xiaozhi-server/docker-compose_all.yml`
- 容器名：`feedback-h5`、`feedback-backend`、`xiaozhi-esp32-server-db` 等
- 入口端口：`8007`
- 数据目录：`../xiaozhi-server/mysql/data`、`../xiaozhi-server/data`

测试环境通过 `../xiaozhi-server/docker-compose.test.yml` 使用独立项目名、独立容器名、独立端口和独立数据目录，避免影响生产。

## 端口约定

| 服务 | 生产 | 测试 |
| --- | ---: | ---: |
| feedback-h5 入口 | 8007 | 18007 |
| xiaozhi WS | 18000 | 28000 |
| xiaozhi HTTP | 18003 | 28003 |
| manager-api | 8002 | 18002 |
| MySQL | 13306 | 23306 |

## 启动

在仓库根目录执行：

```powershell
# 真实 LLM 密钥只放本机环境变量，不提交到 git
$env:FEEDBACK_LLM_PROVIDER = "deepseek"
$env:FEEDBACK_LLM_API_KEY = "你的真实密钥"
$env:FEEDBACK_LLM_BASE_URL = "https://api.deepseek.com/v1"
$env:FEEDBACK_LLM_MODEL = "deepseek-chat"

docker compose -p xiaozhi-feedback-test -f "main/xiaozhi-server/docker-compose.test.yml" up -d --build
```

访问：

- H5：<http://127.0.0.1:18007/>
- Admin：<http://127.0.0.1:18007/admin/>
- API 健康检查：<http://127.0.0.1:18007/health>

## 停止

```powershell
docker compose -p xiaozhi-feedback-test -f "main/xiaozhi-server/docker-compose.test.yml" down
```

如需清空测试库和测试数据：

```powershell
docker compose -p xiaozhi-feedback-test -f "main/xiaozhi-server/docker-compose.test.yml" down -v
Remove-Item -Recurse -Force "main/xiaozhi-server/mysql-test", "main/xiaozhi-server/data-test" -ErrorAction SilentlyContinue
```

> 注意：不要对生产 compose 执行 `down -v`。生产公网 `feedback-admin.new123.vip` 仍回源到本机生产入口 `8007`。
