# Claude Code Web Terminal（中文）

把本机的 **Claude Code CLI** 通过浏览器终端暴露出来，让你可以在浏览器里控制当前电脑上的 Claude Code，并在指定项目目录里工作。

> 本工具使用 [`ttyd`](https://github.com/tsl0922/ttyd) 提供浏览器终端。公网访问推荐使用：Tailscale Funnel + Nginx + Basic Auth。

---

## 这个工具解决什么问题？

Claude Code 本质上是一个本地 CLI 工具。它需要在终端里运行。

但有时你可能希望：

- 不用远程桌面，也能在浏览器里控制本机 Claude Code；
- 从手机、平板、另一台电脑访问当前电脑的 Claude Code；
- 让 Claude Code 仍然在本机运行，继续使用本机文件、本机权限、本机 Git、本机环境变量；
- 打开网页后直接进入指定项目目录；
- 用一个简单的公网域名访问自己的本机开发环境。

本项目不是 Claude Code 官方 Web UI，而是一个“浏览器终端方案”：

```text
浏览器里打开终端 -> 在终端里运行 claude
```

---

## 架构图

```text
浏览器
  -> https://cc.example.com
  -> Nginx 反向代理 + Basic Auth
  -> Tailscale Funnel
  -> 本机 127.0.0.1:18792
  -> ttyd
  -> cmd.exe / PowerShell / bash
  -> claude
```

推荐端口规划：

```text
本机 ttyd:      http://127.0.0.1:18792
Tailscale URL:  https://你的机器名.tailnet.ts.net:18790
公网域名:       https://cc.example.com
```

---

## 安全警告

这个工具会把你电脑上的终端暴露到浏览器。

能访问这个终端的人，理论上可以：

- 查看和修改你的文件；
- 执行命令；
- 使用本机环境变量；
- 使用本机登录状态和凭据；
- 运行 Git 操作；
- 使用 Claude Code 工具；
- 对电脑造成破坏。

所以一定不要裸奔公网。

最低安全建议：

- `ttyd` 只绑定 `127.0.0.1`；
- 不直接开放本机端口到公网；
- 使用 Tailscale Funnel 或其他安全隧道；
- 公网 Nginx 前面加 Basic Auth；
- 使用 HTTPS；
- 使用强密码；
- 不用时关闭 Funnel；
- 尽量不要用管理员/root 权限运行；
- 更安全的做法是使用专门的低权限系统用户。

---

## 环境要求

### 本机

- Windows 10/11、macOS 或 Linux；
- 已安装并登录 Claude Code；
- 已安装 `ttyd`；
- 如需公网访问，建议安装 Tailscale。

### 公网服务器（可选）

- Nginx；
- HTTPS 证书；
- Basic Auth 密码文件；
- 能访问你的 Tailscale Funnel 地址。

---

## Windows 本地快速开始

### 1. 安装 Claude Code

确认本机已经安装 Claude Code：

```powershell
claude --version
```

示例输出：

```text
2.x.x (Claude Code)
```

---

### 2. 安装 ttyd

使用 winget 安装：

```powershell
winget install --id tsl0922.ttyd
```

如果安装后 `ttyd` 命令暂时找不到，可以重启 PowerShell，或者使用完整路径。

常见安装路径：

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\tsl0922.ttyd_Microsoft.Winget.Source_8wekyb3d8bbwe\ttyd.exe
```

---

### 3. 配置 `.env`

复制示例配置：

```powershell
copy .env.example .env
```

编辑 `.env`：

```env
PROJECT_DIR=E:\code\learn_p\xiaozhi-esp32-server
LOCAL_HOST=127.0.0.1
LOCAL_PORT=18792
SHELL_CMD=cmd.exe
FUNNEL_PORT=18790
```

字段说明：

| 字段 | 说明 |
|---|---|
| `PROJECT_DIR` | 打开终端后默认所在目录 |
| `LOCAL_HOST` | 本地绑定地址，推荐固定为 `127.0.0.1` |
| `LOCAL_PORT` | 本地 ttyd 端口 |
| `SHELL_CMD` | 启动的 shell，Windows 推荐 `cmd.exe` |
| `FUNNEL_PORT` | Tailscale Funnel 对外端口 |

---

### 4. 启动本地浏览器终端

```powershell
.\scripts\start-windows.ps1
```

本机打开：

```text
http://127.0.0.1:18792/
```

如果看到浏览器终端，说明启动成功。

然后输入：

```bat
claude
```

如果没有在项目目录，可以先输入：

```bat
cd /d E:\code\learn_p\xiaozhi-esp32-server
claude
```

---

## 推荐启动方式

最稳定的方式是：先启动普通终端，再手动输入 `claude`。

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\code\learn_p\xiaozhi-esp32-server" cmd.exe
```

进入网页终端后再输入：

```bat
claude
```

为什么不建议直接自动启动 Claude Code？

因为在部分 Windows PTY 环境中，直接让 Web 终端启动复杂交互程序可能不稳定。先启动 `cmd.exe`，再手动输入 `claude`，通常更可靠。

如果你仍然想尝试自动启动：

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\code\learn_p\xiaozhi-esp32-server" cmd.exe /k claude
```

---

## 使用 Tailscale Funnel 暴露公网

如果你要从外网访问本机终端，可以使用 Tailscale Funnel。

例如：公网 `18790` 转发到本地 `18792`：

```powershell
tailscale funnel --bg --https=18790 18792
```

查看状态：

```powershell
tailscale serve status
```

你应该看到类似：

```text
https://your-machine.your-tailnet.ts.net:18790
|-- / proxy http://127.0.0.1:18792
```

关闭 Funnel：

```powershell
tailscale funnel --https=18790 off
```

---

## 使用公网 Nginx 反向代理

可以参考：

```text
nginx/cc.example.com.conf
```

关键配置：

```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 86400s;
proxy_send_timeout 86400s;
proxy_buffering off;
```

同时需要在 Nginx 的 `http {}` 或 `conf.d` 中配置：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

---

## Basic Auth 认证

强烈建议公网 Nginx 加 Basic Auth。

生成密码文件：

```bash
sudo sh -c 'printf "claude:%s\n" "$(openssl passwd -apr1 YOUR_STRONG_PASSWORD)" > /etc/nginx/.htpasswd-cc'
sudo chmod 640 /etc/nginx/.htpasswd-cc
sudo chown root:www-data /etc/nginx/.htpasswd-cc
```

Nginx 中启用：

```nginx
auth_basic "Claude Code Web";
auth_basic_user_file /etc/nginx/.htpasswd-cc;
```

---

## 日常使用流程

1. 本机启动 ttyd：

   ```powershell
   .\scripts\start-windows.ps1
   ```

2. 如需公网访问，启动 Funnel：

   ```powershell
   tailscale funnel --bg --https=18790 18792
   ```

3. 打开公网域名：

   ```text
   https://cc.example.com/
   ```

4. 登录 Basic Auth。

5. 在浏览器终端中输入：

   ```bat
   claude
   ```

6. 正常使用 Claude Code。

7. 使用完成后可以关闭浏览器标签页。

8. 长时间不用建议关闭公网 Funnel：

   ```powershell
   tailscale funnel --https=18790 off
   ```

---

## 停止本地服务

```powershell
.\scripts\stop-windows.ps1
```

或者手动停止：

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'ttyd.*18792' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## 常见问题

### 1. 页面能打开，但输入没反应

通常是 WebSocket 没连上。

检查：

- 浏览器 DevTools -> Network -> WS；
- Nginx `/ws` 是否返回 `101 Switching Protocols`；
- 本机 `ttyd` 是否还在运行；
- Tailscale Funnel 是否指向正确端口。

本机检查：

```powershell
curl.exe -I http://127.0.0.1:18792/
```

Nginx 检查：

```bash
curl -k -i --http1.1 \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  -H 'Sec-WebSocket-Version: 13' \
  https://cc.example.com/ws
```

正常应该返回：

```http
HTTP/1.1 101 Switching Protocols
```

---

### 2. 页面还在请求 `/socket.io`

如果之前用过 WeTTY，浏览器可能还缓存着旧的 Service Worker。

解决方法：

- 打开 DevTools；
- Application -> Service Workers -> Unregister；
- Application -> Storage -> Clear site data；
- 刷新页面；
- 或者直接用无痕窗口打开。

---

### 3. 出现 `sw.js chrome-extension` 报错

类似：

```text
Failed to execute 'put' on 'Cache': Request scheme 'chrome-extension' is unsupported
```

通常是浏览器插件或旧 Service Worker 缓存导致的，不一定是服务器问题。

解决方法：

- 无痕窗口测试；
- 禁用可疑浏览器插件；
- 清理站点数据。

---

### 4. Windows 命令一打开就退出

不要直接自动启动 Claude Code，先启动普通 shell：

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\path\to\repo" cmd.exe
```

然后手动输入：

```bat
claude
```

---

### 5. 端口冲突

如果 `18792` 被占用，修改 `.env`：

```env
LOCAL_PORT=18793
```

并同步修改 Tailscale Funnel：

```powershell
tailscale funnel --https=18790 off
tailscale funnel --bg --https=18790 18793
```

---

### 6. Tailscale Funnel 指错端口

查看：

```powershell
tailscale serve status
```

如果不对，重置：

```powershell
tailscale funnel --https=18790 off
tailscale funnel --bg --https=18790 18792
```

---

## 加固建议

如果你准备开源给别人使用，建议提醒用户：

- 使用强密码；
- 使用 HTTPS；
- 限制 IP 访问；
- 不使用管理员/root 用户运行；
- 使用单独系统用户运行；
- 不用时关闭公网入口；
- 对敏感环境使用 VPN/Zero Trust；
- 记录访问日志；
- 不要把 `.env`、密码文件提交到仓库。

---

## FAQ

### 这是 Claude Code 官方网页版本吗？

不是。

Claude Code 是 CLI 工具。本项目只是把本机终端通过浏览器展示出来，然后你在里面运行 `claude`。

---

### 可以多人同时用吗？

技术上可以，但不推荐直接多人共用同一个系统用户。

更安全的方式是：

- 每个人独立系统用户；
- 每个人独立工作目录；
- 或者使用隔离容器/虚拟机。

---

### 支持 macOS / Linux 吗？

支持。

把 Windows 的 `cmd.exe` 换成对应 shell 即可。

Linux/macOS 示例：

```bash
ttyd -i 127.0.0.1 -p 18792 -W -w /path/to/repo bash
```

---

### 是否必须使用 Tailscale？

不是。

你也可以使用：

- Cloudflare Tunnel；
- FRP；
- SSH Tunnel；
- 内网 VPN；
- Nginx 直接反代。

但无论哪种方式，都必须做好认证。

---

### 能不能打开网页就自动进入 Claude Code？

可以尝试，但不一定稳定。

推荐方式：

```text
先进入普通终端 -> 手动输入 claude
```

这样兼容性最好。

---

## License

开源前请确定许可证。

如果只是工具模板，推荐使用 MIT License。
