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
