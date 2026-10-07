# 开发环境端口与启动约定

新同学第一次拉代码跑后端时最常踩的坑：机器上可能有多个 `vue-cli-service` 实例在不同端口运行，`curl 127.0.0.1:8002` 拿到 SPA HTML 误以为后端已起。本文档统一约定端口、启动命令和排查方法。

## 端口分配

| 服务 | 默认端口 | 端口被占时 | 说明 |
| --- | --- | --- | --- |
| manager-api（Java 后端） | `8002` | 启动失败，需手动释放 | Tomcat 默认端口；通过 `application.yml` 中 `server.port` 改 |
| manager-web（Vue 前端 dev） | `8001` | `vue-cli-service` 自动顺延到 `8002/8003/...` | 配置在 `main/manager-web/vue.config.js` 的 `devServer.port` |

后端固定 `8002` 是因为 manager-web 的 `vue.config.js` 把 `/xiaozhi` 反向代理到 `http://127.0.0.1:8002`，改了后端端口必须同步改前端代理，否则 dev 页所有请求 404。

## 启动命令

### 后端 manager-api

```bash
cd main/manager-api
# 必传数据库密码（不要写明文进配置文件或提交）：
mvn spring-boot:run \
  -Dspring-boot.run.profiles=dev \
  -Dspring-boot.run.arguments="--spring.datasource.druid.password=$DB_PASSWORD"
```

成功标志：日志出现 `Tomcat started on port 8002 (http) with context path '/xiaozhi'` 且 `Started AdminApplication in N seconds`。最后两行同时出现才算真起来了。

### 前端 manager-web

```bash
cd main/manager-web
npm install      # 首次或升级依赖
npm run serve    # 默认 8001，被占时看控制台输出的 Local URL
```

成功标志：控制台输出 `App running at: - Local: http://localhost:8001/`（或顺延后的端口）。如果输出 `Local: http://localhost:8002/`，说明 `8001` 被占了 ——**这时 `8002` 是前端 dev server 不是后端**，见下文排查。

## 进程名约定

排查时用 `ps aux | grep` 区分：

| 进程 | grep 关键词 |
| --- | --- |
| 后端 manager-api | `AdminApplication` 或 `manager-api/target/classes` |
| 前端 manager-web dev | `vue-cli-service serve` 或 `manager-web/node_modules/.bin/vue-cli-service` |

示例：

```bash
# 看后端是否真起来
ps aux | grep -E "AdminApplication|manager-api/target" | grep -v grep

# 看前端 dev 在哪个端口
ps aux | grep "vue-cli-service serve" | grep -v grep

# 看谁占了 8002
ss -tlnp | grep ':8002'
```

## 排查：8002 上跑的到底是后端还是前端？

- 浏览器或 `curl -i http://127.0.0.1:8002/` 拿到 `Knife4j` 页面或 JSON 响应 → 后端。
- 拿到 `<!DOCTYPE html>` 含 `id="app"`、`<script src="/js/app.js">` 这类 SPA HTML → 前端 dev server，不是后端。

如果 8002 上跑的是前端：
1. 释放占用的端口：`ss -tlnp | grep ':8002'` 拿到 PID 后 `kill -9 <PID>`。
2. 重启后端 `mvn spring-boot:run`，日志确认 `Tomcat started on port 8002`。
3. 前端 dev server 此时通常已顺延到 `8003`，浏览器手动跳到新端口即可。

## 常见误判

- `curl http://127.0.0.1:8002/xiaozhi/...` 看起来像后端在响应：其实是前端 dev 的 `/xiaozhi` 代理，**代理目标是你环境变量 `VUE_APP_API_BASE_URL` 配置的后端**，可能不是你本机的 8002。检查 `.env.development` 与 `vue.config.js` 的 `proxy.target`。
- 多个旧会话残留 vue-cli 进程：常见于并发跑多个分支时忘了关 dev server，`ss -tlnp` 能一眼看到。
