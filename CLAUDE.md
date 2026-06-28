# CLAUDE.md

## 反馈后台公网部署前置信息

`feedback-admin.new123.vip` 不是在公网服务器本机托管静态文件；公网服务器只做 Nginx 反向代理。

当前目标链路：

```text
浏览器
  -> https://feedback-admin.new123.vip/admin/
  -> 公网服务器 Nginx（ubuntu@100.66.236.1，配置 /etc/nginx/sites-enabled/new123.vip）
  -> Tailscale 到本地 Windows：100.116.124.21:8007
  -> 本地 Docker 容器 feedback-h5
  -> 挂载的本仓库 main/feedback-backend/admin-ui
```

API 与后台 AI 数字人长连接也走同一条 Tailscale 链路：

```text
https://feedback-admin.new123.vip/api/v1/*       -> http://100.116.124.21:8007/api/v1/*
wss://feedback-admin.new123.vip/api/v1/agent/chat/ws -> http://100.116.124.21:8007/api/v1/agent/chat/ws
```

本地关键服务：

- Windows Tailscale IP：`100.116.124.21`（机器名 `kobe-wins-book`）
- 公网服务器 Tailscale IP：`100.66.236.1`（SSH：`ubuntu@100.66.236.1`）
- 本地入口容器：`feedback-h5`，宿主机端口 `8007`
- Compose 文件：`main/xiaozhi-server/docker-compose_all.yml`
- `feedback-h5` 必须挂载：`../feedback-backend/admin-ui:/feedback-backend/admin-ui`

注意：不要再把 admin 静态文件发布到公网服务器 `/var/www/feedback-admin/admin-ui/`。该目录已清空，避免占用服务器磁盘和干扰线上调试。修改后台页面时，改本地仓库并确保 `feedback-h5` 容器重建/已挂载即可。

常用检查：

```powershell
docker ps --format "{{.Names}}\t{{.Ports}}"
docker inspect feedback-h5 --format '{{json .Mounts}}'
docker compose -f "main/xiaozhi-server/docker-compose_all.yml" up -d --force-recreate feedback-h5
```

远端检查：

```bash
ssh ubuntu@100.66.236.1 "sudo nginx -t && sudo nginx -T | grep -nE 'feedback-admin|100.116.124.21|/admin/|/api/v1/'"
```
