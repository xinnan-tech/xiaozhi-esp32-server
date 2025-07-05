# MQTT+UDP 到 WebSocket 桥接服务

## 项目概述

这是一个用于物联网设备通信的桥接服务，实现了MQTT和UDP协议到WebSocket的转换。该服务允许设备通过MQTT协议进行控制消息传输，同时通过UDP协议高效传输音频数据，并将这些数据桥接到WebSocket服务。

## 功能特点

- **多协议支持**: 同时支持MQTT、UDP和WebSocket协议
- **音频数据传输**: 专为音频数据流优化的传输机制
- **加密通信**: 使用AES-128-CTR加密UDP数据传输
- **会话管理**: 完整的设备会话生命周期管理
- **自动重连**: 连接断开时自动重连机制
- **心跳检测**: 定期检查连接活跃状态
- **开发/生产环境配置**: 支持不同环境的配置切换

## 技术架构

- **MQTT服务器**: 处理设备控制消息
- **UDP服务器**: 处理高效的音频数据传输
- **WebSocket客户端**: 连接到聊天服务器
- **桥接层**: 在不同协议间转换和路由消息

## 项目结构

```
├── app.js                # 主应用入口
├── mqtt-protocol.js      # MQTT协议实现
├── ecosystem.config.js   # PM2配置文件
├── package.json          # 项目依赖
├── .env                  # 环境变量配置
├── utils/
│   ├── config-manager.js # 配置管理工具
│   ├── mqtt_config_v2.js # MQTT配置验证工具
│   └── weixinAlert.js    # 微信告警工具
└── config/               # 配置文件目录
```

## 依赖项

- **debug**: 调试日志输出
- **dotenv**: 环境变量管理
- **ws**: WebSocket客户端
- **events**: Node.js 事件模块

## 安装要求

- Node.js 14.x 或更高版本
- npm 或 yarn 包管理器
- PM2 (用于生产环境部署)

## 安装步骤

1. 克隆仓库
```bash
git clone <仓库地址>
cd mqtt-websocket-bridge
```

2. 安装依赖
```bash
npm install
```

3. 创建配置文件
```bash
mkdir -p config
cp config/mqtt.json.example config/mqtt.json
```

4. 编辑配置文件 `config/mqtt.json`，设置适当的参数

## 配置说明

配置文件 `config/mqtt.json` 需要包含以下内容:

```json
{
  "debug": false,
  "development": {
    "mac_addresss": ["aa:bb:cc:dd:ee:ff"],
    "chat_servers": ["wss://dev-chat-server.example.com/ws"]
  },
  "production": {
    "chat_servers": ["wss://chat-server.example.com/ws"]
  }
}
```

## 环境变量

创建 `.env` 文件并设置以下环境变量:

```
MQTT_PORT=1883       # MQTT服务器端口
UDP_PORT=8884        # UDP服务器端口
PUBLIC_IP=your-ip    # 服务器公网IP
```

## 运行服务

### 开发环境

```bash
# 直接运行
node app.js

# 调试模式运行
DEBUG=mqtt-server node app.js
```

### 生产环境 (使用PM2)

```bash
# 安装PM2
npm install -g pm2

# 启动服务
pm2 start ecosystem.config.js

# 查看日志
pm2 logs xz-mqtt

# 监控服务
pm2 monit
```

服务将在以下端口启动:
- MQTT 服务器: 端口 1883 (可通过环境变量修改)
- UDP 服务器: 端口 8884 (可通过环境变量修改)

## 协议说明

### 设备连接流程

1. 设备通过MQTT协议连接到服务器
2. 设备发送 `hello` 消息，包含音频参数和特性
3. 服务器创建WebSocket连接到聊天服务器
4. 服务器返回UDP连接参数给设备
5. 设备通过UDP发送音频数据
6. 服务器将音频数据转发到WebSocket
7. WebSocket返回的控制消息通过MQTT发送给设备

### 消息格式

#### Hello 消息 (设备 -> 服务器)
```json
{
  "type": "hello",
  "version": 3,
  "audio_params": { ... },
  "features": { ... }
}
```

#### Hello 响应 (服务器 -> 设备)
```json
{
  "type": "hello",
  "version": 3,
  "session_id": "uuid",
  "transport": "udp",
  "udp": {
    "server": "server-ip",
    "port": 8884,
    "encryption": "aes-128-ctr",
    "key": "hex-encoded-key",
    "nonce": "hex-encoded-nonce"
  },
  "audio_params": { ... }
}
```

## 安全说明

- UDP通信使用AES-128-CTR加密
- 每个会话使用唯一的加密密钥
- 使用序列号防止重放攻击
- 设备通过MAC地址进行身份验证
- 支持设备分组和UUID验证

## 性能优化

- 使用预分配的缓冲区减少内存分配
- UDP协议用于高效传输音频数据
- 定期清理不活跃的连接
- 连接数和活跃连接数监控
- 支持多聊天服务器负载均衡

## 故障排除

- 检查设备MAC地址格式是否正确
- 确保UDP端口在防火墙中开放
- 启用调试模式查看详细日志
- 检查配置文件中的聊天服务器地址是否正确
- 验证设备认证信息是否正确

## 开发指南

### 添加新功能

1. 修改 `mqtt-protocol.js` 以支持新的MQTT功能
2. 在 `MQTTConnection` 类中添加新的消息处理方法
3. 更新配置管理器以支持新的配置选项
4. 在 `WebSocketBridge` 类中添加新的WebSocket处理逻辑

### 调试技巧

```bash
# 启用所有调试输出
DEBUG=* node app.js

# 只启用MQTT服务器调试
DEBUG=mqtt-server node app.js
```
