# Visual Model Usage Guide
This tutorial is divided into two parts:
- Part 1: Run xiaozhi-server as a single module to start the visual model
- Part 2: How to enable the visual model when all modules are running

Before starting the visual model, you need to prepare three things:
- You need to prepare a device with a camera, and this device is already in the Xiage warehouse and has the camera function enabled. For example, the LiChuang Practical ESP32-S3 Development Board
- Upgrade your device's firmware to version 1.6.6 or above
- You have successfully completed the basic dialogue module

## Single module running xiaozhi-server to start the visual model

### Step 1: Confirm the network
Because the visual model will start port 8003 by default.

If you are running docker, please confirm whether your `docker-compose.yml` has the `8003` port. If not, update the latest `docker-compose.yml` file

If you are running from source code, make sure your firewall is allowing access to port 8003.

### Step 2: Choose your visual model
Open your `data/.config.yaml` file and set `selected_module.VLLM` to a visual model. Currently, we support visual models with `openai` type interfaces. `ChatGLMVLLM` is one of the models compatible with `openai`.

```
selected_module:
  VAD: ..
  ASR: ..
  LLM: ..
  VLLM: ChatGLMVLLM
  TTS: ..
  Memory: ..
  Intent: ..
```

Assuming we use `ChatGLMVLLM` as the visual model, we need to log in to the [Zhipu AI](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) website to apply for a key. If you have already applied for a key, you can reuse it.

In your configuration file, add this configuration. If you already have this configuration, set your api_key.

```
VLLM:
  ChatGLMVLLM:
    api_key: your api_key
```

### The third step is to start the xiaozhi-server service
If you are using source code, enter the command to start
```
python app.py
```
If you are running in docker, restart the container
```
docker restart xiaozhi-esp32-server
```

After startup, the following log will be output.

```
2025-06-01 **** - OTA interface is http://192.168.4.7:8003/xiaozhi/ota/
2025-06-01 **** - The visual analysis interface is http://192.168.4.7:8003/mcp/vision/explain
2025-06-01 **** - Websocket address is ws://192.168.4.7:8000/xiaozhi/v1/
2025-06-01 **** - =======The above address is a websocket protocol address, please do not access it with a browser=======
2025-06-01 **** - If you want to test websocket, please use Google Chrome to open the test_page.html in the test directory.
2025-06-01 **** - =============================================================
```

After startup, use a browser to open the `Visual Analysis Interface` connection in the log to see what is output. If you are using Linux and don't have a browser, you can execute this command:
```
curl -i your visual analysis interface
```

Normally it will display like this
```
The MCP Vision interface is running normally. The visual explanation interface address is: http://xxxx:8003/mcp/vision/explain
```

Please note that if you are deploying on the public network or in docker, you must change the configuration in your `data/.config.yaml`
```
server:
  vision_explain: http://your ip or domain name:port number/mcp/vision/explain
```

Why? Because the visual interpretation interface needs to be sent to the device. If your address is a LAN address or an internal address of Docker, the device cannot be accessed.

Assuming your public network address is `111.111.111.111`, then `vision_explain` should be configured like this:

```
server:
  vision_explain: http://111.111.111.111:8003/mcp/vision/explain
```

If your MCP Vision interface is running normally and you have also tried to use a browser to access the `visual interpretation interface address` that is normally opened, please continue to the next step

### Step 4: Device wake-up and start

Say to the device "Please turn on the camera and tell me what you see"

Pay attention to the log output of xiaozhi-server to see if there are any errors.


## How to enable the visual model when running all modules

### Step 1: Confirm the network
Because the visual model will start port 8003 by default.

If you are running docker, please confirm whether your `docker-compose_all.yml` has mapped `8003` port. If not, update the latest `docker-compose_all.yml` file

If you are running from source code, make sure your firewall is allowing access to port 8003.

### Step 2 Confirm your configuration file

Open your `data/.config.yaml` file and confirm whether the structure of your configuration file is the same as `data/config_from_api.yaml`. If it is different or missing, please fill it in.

### The third step is to configure the visual model key

Then we need to log in to the [Zhipu AI](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) website to apply for a key. If you have already applied for a key, you can reuse it.

Log in to the Smart Console, click Model Configuration on the top menu, click Vision and Language Model on the left sidebar, find VLLM_ChatGLMVLLM, click Modify, enter your key in the API Key field, and click Save.

After successfully saving, go to the agent you want to test, click Configure Actor, and in the context that opens, check that the Vision Large Language Model (VLLM) is selected. Click Save.

### The third step is to start the xiaozhi-server module
If you are using source code, enter the command to start
```
python app.py
```
If you are running in docker, restart the container
```
docker restart xiaozhi-esp32-server
```

After startup, the following log will be output.

```
2025-06-01 **** - The visual analysis interface is http://192.168.4.7:8003/mcp/vision/explain
2025-06-01 **** - Websocket address is ws://192.168.4.7:8000/xiaozhi/v1/
2025-06-01 **** - =======The above address is a websocket protocol address, please do not access it with a browser=======
2025-06-01 **** - If you want to test websocket, please use Google Chrome to open the test_page.html in the test directory.
2025-06-01 **** - =============================================================
```

After startup, use a browser to open the `Visual Analysis Interface` connection in the log to see what is output. If you are using Linux and don't have a browser, you can execute this command:
```
curl -i your visual analysis interface
```

Normally it will display like this
```
The MCP Vision interface is running normally. The visual explanation interface address is: http://xxxx:8003/mcp/vision/explain
```

Please note that if you are deploying on the public network or in docker, you must change the configuration in your `data/.config.yaml`
```
server:
  vision_explain: http://your ip or domain name:port number/mcp/vision/explain
```

Why? Because the visual interpretation interface needs to be sent to the device. If your address is a LAN address or an internal address of Docker, the device cannot be accessed.

Assuming your public network address is `111.111.111.111`, then `vision_explain` should be configured like this:

```
server:
  vision_explain: http://111.111.111.111:8003/mcp/vision/explain
```

If your MCP Vision interface is running normally and you have also tried to use a browser to access the `visual interpretation interface address` that is normally opened, please continue to the next step

### Step 4: Device wake-up and start

Say to the device "Please turn on the camera and tell me what you see"

Pay attention to the log output of xiaozhi-server to see if there are any errors.
