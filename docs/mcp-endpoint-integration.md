# MCP 接入点部署使用指南

本教程包含2个部分
- 1、如何开启mcp接入点
- 2、如何为智能体接入一个简单的mcp功能，如计算器功能

部署的前提条件：
- 1、你已经部署了全模块，因为mcp接入点需要全模块中的智控台功能
- 2、你想在不修改xiaozhi-server项目的前提下，扩展小智的功能

# 如何开启mcp接入点

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
======================================================
接口地址: http://172.1.1.1:8004/mcp_endpoint/health?key=xxxx
=======上面的地址是MCP接入点地址，请勿泄露给任何人============
```

请你把接口地址复制出来：

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

你先把地址复制出来，放在一个草稿里，你要知道你的电脑的局域网ip是什么，例如我的电脑局域网ip是`192.168.1.25`，那么
原来我的接口地址
```
http://172.1.1.1:8004/mcp_endpoint/health?key=xxxx
```
就要改成
```
http://192.168.1.25:8004/mcp_endpoint/health?key=xxxx
```

改好后，请使用浏览器直接访问这个接口。当浏览器出现类似这样的代码，说明是成功了。
```
{"result":{"status":"success","connections":{"tool_connections":0,"robot_connections":0,"total_connections":0}},"error":null,"id":null,"jsonrpc":"2.0"}
```

请你保留好这个`接口地址`，下一步要用到。

## 第三步，配置智控台

使用管理员账号，登录智控台，点击顶部`参数字典`，选择`参数管理`功能。

然后搜索参数`server.mcp_endpoint`，此时，它的值应该是`null`值。
点击修改按钮，把上一步得来的`接口地址`粘贴到`参数值`里。然后保存。

如果能保存成功，说明一切顺利，你可以去智能体查看效果了。如果不成功，说明智控台无法访问mcp接入点，很大概率是网络防火墙，或者没有填写正确的局域网ip。

# 如何为智能体接入一个简单的mcp功能，如计算器功能

如果以上步骤顺利，你可以进入智能体管理，点击`配置角色`，在`意图识别`的右边，有一个`编辑功能`的按钮。

点击这个按钮。在弹出的页面里，位于底部，会有`MCP接入点`，正常来说，会显示这个智能体的`MCP接入点地址`，接下来，我们来给这个智能体扩展一个基于MCP技术的计算器的功能。

这个`MCP接入点地址`很重要，你等一下会用到。

## 第一步 下载虾哥MCP计算器项目代码

浏览器打开虾哥写的[计算器项目](https://github.com/78/mcp-calculator)，

打开完，找到页面中一个绿色的按钮，写着`Code`的按钮，点开它，然后你就看到`Download ZIP`的按钮。

点击它，下载本项目源码压缩包。下载到你电脑后，解压它，此时它的名字可能叫`mcp-calculatorr-main`
你需要把它重命名成`mcp-calculator`。接下来，我们用命令行进入项目目录即安装依赖


```bash
# 进入项目目录
cd mcp-calculator

conda remove -n mcp-calculator --all -y
conda create -n mcp-calculator python=3.10 -y
conda activate mcp-calculator

pip install -r requirements.txt
```

## 第二步 启动

启动前，先从你的智控台的智能体里，复制到了MCP接入点的地址。

例如我的智能体的mcp地址是
```
ws://192.168.4.7:8004/mcp_endpoint/mcp/?token=abc
```

开始输入命令

```bash
export MCP_ENDPOINT=ws://192.168.4.7:8004/mcp_endpoint/mcp/?token=abc
```

输入完后，启动程序

```bash
python mcp_pipe.py calculator.py
```


启动完后，你再进入智控台，点击刷新MCP的接入状态，就会看到你扩展的功能列表了。

