# MCP 接入点部署使用指南

本教程包含2个部分
- 1、如何部署MCP接入点这个服务
- 1、全模块部署时，怎么配置MCP接入点
- 2、单模块部署时，怎么配置MCP接入点

# 1、如何部署MCP接入点这个服务

## 第一步，下载mcp接入点项目源码

浏览器打开[mcp接入点项目地址](https://github.com/xinnan-tech/mcp-endpoint-server)

打开完，找到页面中一个绿色的按钮，写着`Code`的按钮，点开它，然后你就看到`Download ZIP`的按钮。

点击它，下载本项目源码压缩包。下载到你电脑后，解压它，此时它的名字可能叫`mcp-endpoint-server-main`
你需要把它重命名成`mcp-endpoint-server`。

## 第二步，启动程序
这个项目是一个很简单的项目，建议使用docker运行。不过如果你不想使用docker运行，你可以参考[这个页面](https://github.com/xinnan-tech/mcp-endpoint-server/blob/main/README_dev.md)使用源码运行。以下是docker运行的方法

```
# 进入本项目源码根目录
cd mcp-endpoint-server

# 清除缓存
docker compose -f docker-compose.yml down
docker stop mcp-endpoint-server
docker rm mcp-endpoint-server
docker rmi ghcr.nju.edu.cn/xinnan-tech/mcp-endpoint-server:latest

# 启动docker容器
docker compose -f docker-compose.yml up -d
# 查看日志
docker logs -f mcp-endpoint-server
```

此时，日志里会输出类似以下的日志
```
250705 INFO-=====下面的地址分别是智控台/单模块MCP接入点地址====
250705 INFO-智控台MCP参数配置: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
250705 INFO-单模块部署MCP接入点: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
250705 INFO-=====请根据具体部署选择使用，请勿泄露给任何人======
```

请你把两个接口地址复制出来：

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

你先把地址复制出来，放在一个草稿里，你要知道你的电脑的局域网ip是什么，例如我的电脑局域网ip是`192.168.1.25`，那么
原来我的接口地址
```
智控台MCP参数配置: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
单模块部署MCP接入点: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
```
就要改成
```
智控台MCP参数配置: http://192.168.1.25:8004/mcp_endpoint/health?key=abc
单模块部署MCP接入点: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

改好后，请使用浏览器直接访问`智控台MCP参数配置`。当浏览器出现类似这样的代码，说明是成功了。
```
{"result":{"status":"success","connections":{"tool_connections":0,"robot_connections":0,"total_connections":0}},"error":null,"id":null,"jsonrpc":"2.0"}
```

请你保留好上面两个`接口地址`，下一步要用到。

# 2、全模块部署时，怎么配置MCP接入点

如果你是全模块部署，使用管理员账号，登录智控台，点击顶部`参数字典`，选择`参数管理`功能。

然后搜索参数`server.mcp_endpoint`，此时，它的值应该是`null`值。
点击修改按钮，把上一步得来的`智控台MCP参数配置`粘贴到`参数值`里。然后保存。

如果能保存成功，说明一切顺利，你可以去智能体查看效果了。如果不成功，说明智控台无法访问mcp接入点，很大概率是网络防火墙，或者没有填写正确的局域网ip。

# 3、单模块部署时，怎么配置MCP接入点

如果你是单模块部署，找到你的配置文件`data/.config.yaml`。
在配置文件搜索`mcp_endpoint`，如果没有找到，你就增加`mcp_endpoint`配置。类似我是就是这样
```
server:
  websocket: ws://你的ip或者域名:端口号/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# 此处可能还更多配置..

mcp_endpoint: 你的接入点websocket地址
```
这时，请你把`如何部署MCP接入点这个服务`中得到的`单模块部署MCP接入点` 粘贴到 `mcp_endpoint`中。类似这样

```
server:
  websocket: ws://你的ip或者域名:端口号/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# 此处可能还更多配置

mcp_endpoint: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

配置好后，启动单模块会输出如下的日志。
```
250705[__main__]-INFO-初始化组件: vad成功 SileroVAD
250705[__main__]-INFO-初始化组件: asr成功 FunASRServer
250705[__main__]-INFO-OTA接口是          http://192.168.1.25:8002/xiaozhi/ota/
250705[__main__]-INFO-视觉分析接口是     http://192.168.1.25:8002/mcp/vision/explain
250705[__main__]-INFO-mcp接入点是        ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
250705[__main__]-INFO-Websocket地址是    ws://192.168.1.25:8000/xiaozhi/v1/
250705[__main__]-INFO-=======上面的地址是websocket协议地址，请勿用浏览器访问=======
250705[__main__]-INFO-如想测试websocket请用谷歌浏览器打开test目录下的test_page.html
250705[__main__]-INFO-=============================================================
```

如上，如果能输出类似的`mcp接入点是`中`ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc`说明配置成功了。

