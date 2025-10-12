# MCP Access Point Deployment Guide

This tutorial consists of 3 parts
- 1. How to deploy the MCP access point service
- 2. How to configure MCP access points when deploying all modules
- 3. How to configure the MCP access point when deploying a single module

# 1. How to deploy the MCP access point service

## The first step is to download the mcp access point project source code

Open the [mcp access point project address](https://github.com/xinnan-tech/mcp-endpoint-server) in the browser

After opening, find a green button on the page with the word `Code` written on it, click it, and then you will see the `Download ZIP` button.

Click it to download the source code compressed package of this project. After downloading it to your computer, unzip it. At this time, its name may be `mcp-endpoint-server-main`
You need to rename it to `mcp-endpoint-server`.

## Step 2: Start the program
This project is a very simple one and it is recommended to run it using docker. However, if you do not want to use docker, you can refer to [this page](https://github.com/xinnan-tech/mcp-endpoint-server/blob/main/README_dev.md) to run it using the source code. The following is how to run it using docker

```
# Enter the source code root directory of this project
cd mcp-endpoint-server

# Clear the cache
docker compose -f docker-compose.yml down
docker stop mcp-endpoint-server
docker rm mcp-endpoint-server
docker rmi ghcr.nju.edu.cn/xinnan-tech/mcp-endpoint-server:latest

# Start the docker container
docker compose -f docker-compose.yml up -d
# View logs
docker logs -f mcp-endpoint-server
```

At this point, the log will output a log similar to the following
```
250705 INFO-=====The following addresses are the access point addresses of the intelligent control console/single module MCP====
250705 INFO - Intelligent Control Station MCP parameter configuration: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
250705 INFO-Single module deployment MCP access point: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
250705 INFO-=====Please choose to use according to the specific deployment, do not disclose to anyone======
```

Please copy the two interface addresses:

Since you are deploying with docker, do not use the above address directly!

Since you are deploying with docker, do not use the above address directly!

Since you are deploying with docker, do not use the above address directly!

First, copy the address and put it in a draft. You need to know what your computer's LAN IP is. For example, my computer's LAN IP is `192.168.1.25`, then
It turns out that my interface address
```
Intelligent control console MCP parameter configuration: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
Single module deployment MCP access point: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
```
It should be changed to
```
Intelligent control console MCP parameter configuration: http://192.168.1.25:8004/mcp_endpoint/health?key=abc
Single module deployment MCP access point: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

After the modification, please use your browser to directly access the MCP parameter configuration of the intelligent control console. When the browser displays a code similar to this, it means that it is successful.
```
{"result":{"status":"success","connections":{"tool_connections":0,"robot_connections":0,"total_connections":0}},"error":null,"id":null,"jsonrpc":"2.0"}
```

Please keep the above two `Interface Addresses`, as they will be used in the next step.

# 2. How to configure MCP access points when deploying all modules

If you are deploying a full module deployment, use the administrator account to log in to the intelligent console, click the `Parameter Dictionary` at the top, and select the `Parameter Management` function.

Then search for the parameter `server.mcp_endpoint`. At this point, its value should be `null`.
Click the Modify button and paste the MCP Parameter Configuration from the previous step into the Parameter Value field. Then save the value.

If it saves successfully, everything goes well and you can check the effect in the smart body. If it fails, it means that the smart console cannot access the MCP access point. It is likely that there is a network firewall or the correct LAN IP address is not entered.

# 3. How to configure the MCP access point when deploying a single module

If you are deploying a single module, find your configuration file `data/.config.yaml`.
Search `mcp_endpoint` in the configuration file. If you don't find it, add `mcp_endpoint` configuration.
```
server:
  websocket: ws://your ip or domain name:port number/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# There may be more configuration here..

mcp_endpoint: your access point websocket address
```
At this time, please paste the `Single Module Deployment of MCP Access Point` obtained from `How to Deploy MCP Access Point Service` into `mcp_endpoint`.

```
server:
  websocket: ws://your ip or domain name:port number/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# There may be more configuration here

mcp_endpoint: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

After configuration, starting a single module will output the following log.
```
250705[__main__]-INFO-Initialization component: vad successful SileroVAD
250705[__main__]-INFO-Initialization component: asr successful FunASRServer
250705[__main__]-INFO-OTA interface is http://192.168.1.25:8002/xiaozhi/ota/
250705[__main__]-INFO-The visual analysis interface is http://192.168.1.25:8002/mcp/vision/explain
250705[__main__]-INFO-mcp access point is ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
250705[__main__]-INFO-Websocket address is ws://192.168.1.25:8000/xiaozhi/v1/
250705[__main__]-INFO-=======The above address is the websocket protocol address, please do not access it with a browser=======
250705[__main__]-INFO-If you want to test websocket, please use Google Chrome to open the test_page.html in the test directory
250705[__main__]-INFO-================================================================
```

As shown above, if `mcp access point is` similar to `ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc` is output, it means the configuration is successful.
