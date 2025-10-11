# MQTT 网关部署教程

`xiaozhi-esp32-server`项目，可结合虾哥开源的[xiaozhi-mqtt-gateway](https://github.com/78/xiaozhi-mqtt-gateway) 项目进行简单改造，即可实现小智硬件MQTT+UDP连接。
本教程分为三部分，你可以根据你是全模块部署还是单模块部署，选择对应的部分接入MQTT网关：
- 第一部分：部署MQTT网关
- 第二部分：全模块运行实现小智硬件MQTT+UDP连接
- 第三部分：单模块运行xiaozhi-server实现小智硬件MQTT+UDP连接

## 准备阶段
准备好你的`xiaozhi-server`的`mqtt-websocket`连接地址。在你原来的`websocket地址`基础上，添加`?from=mqtt_gateway`字符，就可以得到`mqtt-websocket`连接地址

1、如果你是源码部署，你的`mqtt-websocket`地址是：
```
ws://127.0.0.1:8000/xiaozhi/v1?from=mqtt_gateway
```

2、如果你是docker部署，你的`mqtt-websocket`地址是
```
ws://你宿主机局域网IP:8000/xiaozhi/v1?from=mqtt_gateway
```

## 重要提示

如果你是服务器部署，需要确保服务器`1883`、`8884`、`8007`端口都对外开放。`8884`选择的协议类型是`UDP`，其他是`TCP`。

如果你是服务器部署，需要确保服务器`1883`、`8884`、`8007`端口都对外开放。`8884`选择的协议类型是`UDP`，其他是`TCP`。

如果你是服务器部署，需要确保服务器`1883`、`8884`、`8007`端口都对外开放。`8884`选择的协议类型是`UDP`，其他是`TCP`。


## 第一部分：部署MQTT网关

1. 克隆[改造后的xiaozhi-mqtt-gateway项目](https://github.com/xinnan-tech/xiaozhi-mqtt-gateway.git)：
```bash
git clone https://ghfast.top/https://github.com/xinnan-tech/xiaozhi-mqtt-gateway.git
cd xiaozhi-mqtt-gateway
```

2. 安装依赖：
```bash
npm install
npm install -g pm2
```

3. 配置 `config.json`：
```bash
cp config/mqtt.json.example config/mqtt.json
```

4. 编辑配置文件 config/mqtt.json，把你在`本文准备阶段`的`mqtt-websocket`地址替换到`chat_servers`里。例如源码部署的`xiaozhi-server`就是如下配置：

``` 
{
    "production": {
        "chat_servers": [
            "ws://127.0.0.1:8000/xiaozhi/v1?from=mqtt_gateway"
        ]
    },
    "debug": false,
    "max_mqtt_payload_size": 8192,
    "mcp_client": {
        "capabilities": {
        },
        "client_info": {
            "name": "xiaozhi-mqtt-client",
            "version": "1.0.0"
        },
        "max_tools_count": 128
    }
}
```
5. 在项目根目录创建下`.env`文件，并设置以下环境变量:
```
PUBLIC_IP=your-ip         # 服务器公网IP
MQTT_PORT=1883            # MQTT服务器端口
UDP_PORT=8884             # UDP服务器端口
API_PORT=8007             # 管理API端口
MQTT_SIGNATURE_KEY=test   # MQTT签名密钥
```
请注意`PUBLIC_IP`配置，确保其与实际公网IP一致，如果有域名就填域名。

`MQTT_SIGNATURE_KEY` 是用于MQTT连接认证的密钥，最好设置成复杂一点的，最好是设置成8个字符以上且同时包含大小写字母，这个密钥稍后还会用到。

- 注意不要用简单的密码，比如`123456`、`test`等。
- 注意不要用简单的密码，比如`123456`、`test`等。
- 注意不要用简单的密码，比如`123456`、`test`等。

6. 启动MQTT网关
```
# 启动服务
pm2 start ecosystem.config.js

# 查看日志
pm2 logs xz-mqtt
```

当你看到如下日志，说明MQTT网关启动成功：
```
0|xz-mqtt  | 2025-09-11T12:14:48: MQTT 服务器正在监听端口 1883
0|xz-mqtt  | 2025-09-11T12:14:48: UDP 服务器正在监听 x.x.x.x:8884
```

如果需要重启MQTT网关，执行如下命令：
```
pm2 restart xz-mqtt
```

## 第二部分：全模块运行实现小智硬件MQTT+UDP连接

查看你智控台首页底部的版本号，确认你的智控台版本是否是`0.7.7`及以上版本。如果不是，需要升级智控台。

1. 在智控台顶部，点击`参数管理`，搜索`server.mqtt_gateway`，点击编辑，填入你在`.env`文件中设置的`PUBLIC_IP`+`:`+`MQTT_PORT`。类似这样
```
192.168.0.7:1883
```
2. 在智控台顶部，点击`参数管理`，搜索`server.mqtt_signature_key`，点击编辑，填入你在`.env`文件中设置的`MQTT_SIGNATURE_KEY`。

3. 在智控台顶部，点击`参数管理`，搜索`server.udp_gateway`，点击编辑，填入你在`.env`文件中设置的`PUBLIC_IP`+`:`+`UDP_PORT`。类似这样
```
192.168.0.7:8884
```
4. 在智控台顶部，点击`参数管理`，搜索`server.mqtt_manager_api`，点击编辑，填入你在`.env`文件中设置的`PUBLIC_IP`+`:`+`UDP_PORT`。类似这样
```
192.168.0.7:8007
```

上面的配置完成后，你可以使用curl命令，验证你的ota地址是否会下发mqtt配置，把下面的`http://localhost:8002/xiaozhi/ota/`改成你的ota地址
```
curl 'http://localhost:8002/xiaozhi/ota/' \
  -H 'Content-Type: application/json' \
  -H 'Client-Id: 7b94d69a-9808-4c59-9c9b-704333b38aff' \
  -H 'Device-Id: 11:22:33:44:55:66' \
  --data-raw $'{\n  "application": {\n    "version": "1.0.1",\n    "elf_sha256": "1"\n  },\n  "board": {\n    "mac": "11:22:33:44:55:66"\n  }\n}'
```

如果返回的内容包含`mqtt`相关的配置，说明配置成功。类似这样

```
{"server_time":{"timestamp":1757567894012,"timeZone":"Asia/Shanghai","timezone_offset":480},"activation":{"code":"460609","message":"http://xiaozhi.server.com\n460609","challenge":"11:22:33:44:55:66"},"firmware":{"version":"1.0.1","url":"http://xiaozhi.server.com:8002/xiaozhi/otaMag/download/NOT_ACTIVATED_FIRMWARE_THIS_IS_A_INVALID_URL"},"websocket":{"url":"ws://192.168.4.23:8000/xiaozhi/v1/"},"mqtt":{"endpoint":"192.168.0.7:1883","client_id":"GID_default@@@11_22_33_44_55_66@@@7b94d69a-9808-4c59-9c9b-704333b38aff","username":"eyJpcCI6IjA6MDowOjA6MDowOjA6MSJ9","password":"Y8XP9xcUhVIN9OmbCHT9ETBiYNE3l3Z07Wk46wV9PE8=","publish_topic":"device-server","subscribe_topic":"devices/p2p/11_22_33_44_55_66"}}
```

由于MQTT信息是需要靠OTA地址下发的，因此只有你保证能正常连接服务器的OTA地址，重启唤醒即可。

唤醒后留意mqtt-gateway的日志，确认是否有连接成功的日志。
```
pm2 logs xz-mqtt
```

## 第三部分：全模块运行实现小智硬件MQTT+UDP连接

打开你的`data/.config.yaml`文件，在`server`下找到`mqtt_gateway`填入你在`.env`文件中设置的`PUBLIC_IP`+`:`+`MQTT_PORT`。类似这样
```
192.168.0.7:1883
```
在`server`下找到`mqtt_signature_key`填入你在`.env`文件中设置的`MQTT_SIGNATURE_KEY`。

在`server`下找到`udp_gateway`填入你在`.env`文件中设置的`PUBLIC_IP`+`:`+`UDP_PORT`。类似这样
```
192.168.0.7:8884
```

上面的配置完成后，你可以使用curl命令，验证你的ota地址是否会下发mqtt配置，把下面的`http://localhost:8002/xiaozhi/ota/`改成你的ota地址
```
curl 'http://localhost:8002/xiaozhi/ota/' \
  -H 'Device-Id: 11:22:33:44:55:66' \
  --data-raw $'{\n  "application": {\n    "version": "1.0.1",\n    "elf_sha256": "1"\n  },\n  "board": {\n    "mac": "11:22:33:44:55:66"\n  }\n}'
```

如果返回的内容包含`mqtt`相关的配置，说明配置成功。类似这样
```
{"server_time":{"timestamp":1758781561083,"timeZone":"GMT+08:00","timezone_offset":480},"activation":{"code":"527111","message":"http://xiaozhi.server.com\n527111","challenge":"11:22:33:44:55:66"},"firmware":{"version":"1.0.1","url":"http://xiaozhi.server.com:8002/xiaozhi/otaMag/download/NOT_ACTIVATED_FIRMWARE_THIS_IS_A_INVALID_URL"},"websocket":{"url":"ws://192.168.1.15:8000/xiaozhi/v1/"},"mqtt":{"endpoint":"192.168.1.15:1883","client_id":"GID_default@@@11_22_33_44_55_66@@@11_22_33_44_55_66","username":"eyJpcCI6IjE5Mi4xNjguMS4xNSJ9","password":"fjAYs49zTJecWqJ3jBt+kqxVn/x7vkXRAc85ak/va7Y=","publish_topic":"device-server","subscribe_topic":"devices/p2p/11_22_33_44_55_66"}}
```

由于MQTT信息是需要靠OTA地址下发的，因此只有你保证能正常连接服务器的OTA地址，重启唤醒即可。

唤醒后留意mqtt-gateway的日志，确认是否有连接成功的日志。
```
pm2 logs xz-mqtt
```