# 反馈系统公网部署记录与后续建议

本文记录本次 `feedback.new123.vip`、`feedback-admin.new123.vip` 公网部署/排障结论，便于后续维护。

## 服务器与入口

公网服务器：

```bash
ssh ubuntu@100.66.236.1
```

公网 Nginx 配置文件：

```text
/etc/nginx/sites-enabled/new123.vip
```

配置修改前建议备份到：

```text
/etc/nginx/sites-disabled/
```

常用验证命令：

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo nginx -T
```

## 当前域名规划

### H5 反馈入口

```text
https://feedback.new123.vip/index.html#/home
```

页面和静态资源仍走 `443`。

### H5 语音 WebSocket 与反馈 API

由于 `443` 上公网 WebSocket/部分 API 请求出现过 `ERR_CONNECTION_CLOSED`，已新增稳定专用入口：

```text
wss://feedback.new123.vip:8443/ws/
https://feedback.new123.vip:8443/api/v1/...
```

`feedback-h5/js/api.js` 通过公网 Nginx 动态替换为：

```js
const FEEDBACK_API_BASE = 'https://feedback.new123.vip:8443/api/v1';
const WS_BASE = 'wss://feedback.new123.vip:8443/ws';
```

8443 已在云安全组放行，Nginx 本机和公网测试均返回 WebSocket `101 Switching Protocols`。

### 反馈后台管理

```text
https://feedback-admin.new123.vip/admin/
```

根路径会跳转：

```text
https://feedback-admin.new123.vip/ -> /admin/
```

后台管理现在采用“公网 Nginx + Tailscale 回源到本地 Windows”的方式，不再在公网服务器托管 admin 静态文件：

```text
浏览器
  -> feedback-admin.new123.vip 公网 Nginx
  -> Tailscale: 100.116.124.21:8007
  -> Windows 本地 Docker feedback-h5
  -> 本仓库 main/feedback-backend/admin-ui
```

公网服务器上旧的后台静态目录已删除/清空，避免占用磁盘和干扰调试：

```text
/var/www/feedback-admin/admin-ui/        # 不再使用
/var/www/feedback-admin/admin-ui.bak-*   # 已清理
```

后台 API 和 AI 数字人长连接也通过同一 Tailscale 入口：

```text
https://feedback-admin.new123.vip/api/v1/...
wss://feedback-admin.new123.vip/api/v1/agent/chat/ws
```

公网 Nginx 的核心配置应保持为：

```nginx
location /admin/ {
    proxy_pass http://100.116.124.21:8007;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
}

location /api/v1/ {
    proxy_pass http://100.116.124.21:8007;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 600s;
    proxy_send_timeout 180s;
    proxy_connect_timeout 30s;
    proxy_buffering off;
}
```

本地必须保证 `feedback-h5` 容器挂载后台静态文件目录：

```yaml
- ../feedback-backend/admin-ui:/feedback-backend/admin-ui
```

如果公网 admin 页面没有更新，优先检查本地容器挂载并重建：

```powershell
docker inspect feedback-h5 --format '{{json .Mounts}}'
docker compose -f "main/xiaozhi-server/docker-compose_all.yml" up -d --force-recreate feedback-h5
```


## 后台账号与权限

### 超级管理员

```text
用户名：admin
密码：admin123
```

> 建议上线后尽快修改默认密码。

管理员可以访问：

- 统计概览
- 反馈记录
- 门店管理
- 员工管理
- 智能体配置

### 门店店长

店长账号默认使用门店编码首次登录，例如：

```text
用户名：558744
密码：558744
```

首次登录会自动创建店长账号，角色为：

```text
store_manager
```

并绑定门店：

```text
store001 / 558744 / 腰妍美容养生馆
```

店长登录后：

- 可访问：统计概览、反馈记录、员工管理
- 不可访问：门店管理、智能体配置
- 后端接口强制按店长门店过滤，不能通过改 URL 查看其他门店数据
- 支持在侧边栏底部修改密码

## 手机端适配

反馈后台已做移动端适配，面向店长手机登录使用：

- 顶部汉堡菜单打开侧边栏
- 登录页自适应手机屏幕
- 统计卡片自动换行
- 表格横向滚动
- 弹窗在手机端呈底部抽屉样式
- 统计图表使用 CSS 响应式条形/柱状图，不再使用被拉伸的 canvas

## 已修复问题

### 1. WebSocket `code 1006`

现象：

```text
WebSocket connection failed
code=1006
```

处理：新增 `8443` 专用 WebSocket 入口，并将公网 H5 的 `WS_BASE` 指向：

```text
wss://feedback.new123.vip:8443/ws
```

### 2. API `ERR_CONNECTION_CLOSED`

现象：

```text
POST /api/v1/public/record net::ERR_CONNECTION_CLOSED
POST /api/v1/public/process net::ERR_CONNECTION_CLOSED
```

处理：公网 H5 的反馈 API 也切到：

```text
https://feedback.new123.vip:8443/api/v1
```

### 3. CORS 重复响应头

现象：

```text
Access-Control-Allow-Origin contains multiple values
```

处理：调整 8443 API CORS，避免同时返回 `*` 和具体域名。

### 4. 后台静态资源改为 Tailscale 回源

历史原因：`feedback-admin` 曾错误返回 H5 首页 HTML，导致 JS 请求拿到 HTML；当时临时将反馈后台静态文件部署到公网服务器本机，并让 Nginx 的 `/admin/` 使用 `alias /var/www/feedback-admin/admin-ui/`。

现状：为节省公网服务器磁盘并避免本地代码与服务器静态文件不一致，`/admin/` 已改为反向代理到 Windows 本地 Tailscale 服务：

```nginx
location /admin/ {
    proxy_pass http://100.116.124.21:8007;
}
```

`/var/www/feedback-admin/admin-ui/` 和历史 `admin-ui.bak-*` 备份目录已清理，不再用于发布。

### 5. 管理后台登录 500

原因：`passlib==1.7.4` 与容器内 `bcrypt==5.0.0` 不兼容。

处理：将 `bcrypt` 固定为兼容版本：

```text
bcrypt==4.0.1
```

并在容器内降级后重启 `feedback-backend`。

## 后续建议

1. **保持本地 Tailscale 回源链路稳定**  
   `feedback-admin.new123.vip` 的 `/admin/`、`/api/v1/` 和后台 AI WebSocket 都通过公网 Nginx 回源到 Windows 本地 `100.116.124.21:8007`。不要再往公网服务器 `/var/www/feedback-admin/admin-ui/` 发布静态文件；该目录已清理。

2. **固化 Docker 镜像**  
   本次有部分代码通过 `docker cp` 快速复制进容器验证。建议后续重新构建 `feedback-backend` 镜像，确保容器重建后权限逻辑和 `bcrypt==4.0.1` 不丢失。

3. **将公网 Nginx 配置纳入版本管理**  
   当前公网 Nginx 配置在服务器 `/etc/nginx/sites-enabled/new123.vip`，建议把稳定版同步回仓库，例如维护一份 `deploy/nginx/new123.vip.conf`。

4. **减少 Nginx 动态 JS 替换**  
   目前公网通过 Nginx 对 H5 `api.js` 做 `sub_filter` 动态替换。长期建议在前端代码中支持生产环境配置文件，例如 `/runtime-config.js` 或环境变量注入。

5. **后台 API 域名统一**  
   当前后台页面在 `feedback-admin.new123.vip`，API 走 `feedback-admin.new123.vip:8443`。长期可考虑单独 API 子域名，例如 `feedback-api.new123.vip`，减少端口暴露。

6. **密码安全**  
   管理员默认密码 `admin123` 和店长初始密码等于门店编码，仅适合初始化。建议上线后要求首次登录强制修改密码。

7. **权限继续细化**  
   店长当前可以管理本门店员工。若后续需要更细权限，可继续区分只读店长、可编辑店长、区域经理等角色。

8. **日志与监控**  
   重点关注：

```text
/var/log/nginx/feedback-admin.access.log
/var/log/nginx/feedback-admin.error.log
/var/log/nginx/feedback-ws8443.access.log
/var/log/nginx/feedback-ws8443.error.log
```

以及本地容器：

```bash
docker logs feedback-backend
```
