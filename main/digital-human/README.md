本文档是开发类文档，如需部署小智服务端，[点击这里查看部署教程](../../README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3)

如需查看一体机数字人落地部署、Kiosk 全屏启动和系统环境配置，[点击这里查看一体机部署指南](../../docs/all-in-one-digital-human-setup.md)

如需查看唤醒词模型下载、运行时配置和详细使用说明，[点击这里查看唤醒词专题文档](../../docs/digital-human-wakeword.md)

# 项目介绍

digital-human 是独立的数字人测试模块，负责提供本地测试页面、前端交互资源、唤醒词运行时和事件桥能力，用于联调整个数字人交互链路。

# 快速启动

安装依赖：

```bash
pip install -r wakeword_runtime/requirements.txt
```

启动模块：

```bash
python start.py
```

# 访问地址

启动后可访问：

- 页面地址：http://127.0.0.1:8006/index.html
- 事件桥地址：ws://127.0.0.1:8006/wakeword-ws
- 健康检查：http://127.0.0.1:8006/health

# 开启认证后的用法

服务端 `config.yaml` 里 `server.auth.enabled` 设为 `true` 时，本页面需要额外的凭证才能连上：

1. **激活码**：向服务端运维要一个码，填进页面的「激活码」输入框。页面请求 OTA 时带上它，服务端换发一次 websocket token，用掉即失效。
2. **设备MAC**：填无分隔符或带冒号的 12 位 MAC 都行，页面会统一去掉分隔符转小写后再发给服务端。OTA 请求头和 websocket 子协议用的是同一个值，签名才对得上。

激活码只能用一次，页面拿到 token 后会自己存着，之后每次 OTA 都用 token 续签，不用再填码。

websocket 的凭证走子协议头而不是 URL：`Sec-WebSocket-Protocol: xiaozhi, t-<token>, d-<deviceId>, c-<clientId>`。浏览器不能自定义 websocket 请求头，服务端握手时只回显 `xiaozhi`。放进 URL 查询串的凭证不再被采信，理由是查询串会原样落进反代访问日志。

## 跨域

服务端默认不下发跨域响应头，页面从别的来源打开时会被浏览器拦掉。跨域失败在浏览器里读不到状态码，只会在控制台报一句不透明的错，所以要让服务端把页面的来源加进白名单：

`http://127.0.0.1:8006` 和 `http://localhost:8006` 是两个不同来源，按上面哪个地址打开就得填哪个，两个都填最省事：

```yaml
server:
  cors:
    allowed_origins:
      - http://127.0.0.1:8006
      - http://localhost:8006
```

`main/digital-human` 里的页面是用 `python start.py` 起 HTTP 服务打开的，不是双击文件；用 `file://` 打开时页面会自己弹窗挡住整页，来源是 `null` 也不必往名单里填。

不开启认证时以上都不用填，行为与之前一致。

# 目录说明

- `start.py`：模块启动入口
- `index.html`：数字人测试页面入口
- `wakeword_runtime`：本地唤醒词运行时与配置目录
- `js`、`css`：页面前端脚本与样式
- `images`、`resources`：页面资源文件

# 相关文档

- 一体机部署指南：适用于 x86 设备整机落地部署、Kiosk 展示和开机自启动配置
	[../../docs/all-in-one-digital-human-setup.md](../../docs/all-in-one-digital-human-setup.md)
- 唤醒词专题文档：适用于唤醒词模型下载、运行时配置和本地调试说明
	[../../docs/digital-human-wakeword.md](../../docs/digital-human-wakeword.md)
