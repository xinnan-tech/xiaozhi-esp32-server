# MCP Access Point User Guide

This tutorial uses the open source MCP calculator function of Xia Ge as an example to introduce how to connect your own customized MCP service to your own access point.

The premise of this tutorial is that the mcp endpoint function has been enabled on your `xiaozhi-server`. If you haven't enabled it yet, you can enable it according to [this tutorial](./mcp-endpoint-enable.md).

# How to access a simple mcp function for the agent, such as a calculator function

### If you are deploying a full module
If you are deploying a full module, you can go to the Intelligent Console, select Agent Management, click Configure Role, and to the right of Intent Recognition, there is an Edit Function button.

Click this button. In the pop-up page, at the bottom, there will be an MCP access point. Normally, it will display the MCP access point address of this agent. Next, we will extend this agent with a calculator function based on MCP technology.

This `MCP access point address` is very important and you will need it later.

### If you are deploying a single module
If you are deploying a single module and you have configured the MCP access point address in the configuration file, then normally, the following log will be output when the single module deployment is started.
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

As shown above, `ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc` in the `mcp access point is` output is your `MCP access point address`.

This `MCP access point address` is very important and you will need it later.

## The first step is to download the MCP calculator project code

Open the [calculator project](https://github.com/78/mcp-calculator) written by Brother Xia in the browser.

After opening, find a green button on the page with the word `Code` written on it, click it, and then you will see the `Download ZIP` button.

Click it to download the source code of this project. After downloading it to your computer, unzip it. At this time, its name may be `mcp-calculatorr-main`
You need to rename it to `mcp-calculator`. Next, we use the command line to enter the project directory to install the dependencies


```bash
# Enter the project directory
cd mcp-calculator

conda remove -n mcp-calculator --all -y
conda create -n mcp-calculator python=3.10 -y
conda activate mcp-calculator

pip install -r requirements.txt
```

## Second step startup

Before starting, copy the address of the MCP access point from the intelligent body of your smart console.

For example, the mcp address of my agent is
```
ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
```

Start typing commands

```bash
export MCP_ENDPOINT=ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
```

After entering, start the program

```bash
python mcp_pipe.py calculator.py
```

### If you are deploying on a smart console
If you are deploying on a smart console, after startup, enter the smart console and click Refresh MCP access status, you will see your expanded function list.

### If you are deploying a single module
If you are deploying a single module, a similar log will be output when the device is connected, indicating success.

```
250705 -INFO-Initializing MCP access point: wss://2662r3426b.vicp.fun/mcp_e
250705 -INFO-Send MCP access point initialization message
250705 -INFO-MCP access point connection successful
250705 -INFO-MCP access point initialization successful
250705 -INFO-Unified tool processor initialization completed
250705 -INFO-MCP access point server information: name=Calculator, version=1.9.4
250705 -INFO - Number of tools supported by MCP access point: 1
250705 -INFO-All MCP access point tools have been obtained and the client is ready
250705 -INFO-Tools cache flushed
250705 -INFO- List of currently supported functions: [ 'get_time', 'get_lunar', 'play_music', 'get_weather', 'handle_exit_intent', 'calculator']
```
If `'calculator'` is included, the device will be able to use the calculator tool based on the intent recognition.
