# MCP Endpoint Deployment and Usage Guide

This tutorial contains 2 parts:
- 1. How to enable the MCP endpoint
- 2. How to integrate a simple MCP function for the AI agent, such as calculator functionality

Prerequisites for deployment:
- 1. You have deployed the full module suite, as the MCP endpoint requires the management console functionality from the full module
- 2. You want to extend Xiaozhi's functionality without modifying the xiaozhi-server project

# How to Enable the MCP Endpoint

## Step 1: Download the MCP Endpoint Project Source Code

Open the [MCP endpoint project repository](https://github.com/xinnan-tech/mcp-endpoint-server) in your browser.

Once opened, find the green button labeled `Code` on the page, click it, and you'll see the `Download ZIP` button.

Click it to download the project source code archive. After downloading to your computer, extract it. The folder name might be `mcp-endpoint-server-main`, which you need to rename to `mcp-endpoint-server`.

## Step 2: Start the Program
This is a simple project, and it's recommended to run it using Docker. However, if you don't want to use Docker, you can refer to [this page](https://github.com/xinnan-tech/mcp-endpoint-server/blob/main/README_dev.md) to run from source code. Here's how to run with Docker:

```bash
# Enter the project source code root directory
cd mcp-endpoint-server

# Clear cache
docker compose -f docker-compose.yml down
docker stop mcp-endpoint-server
docker rm mcp-endpoint-server
docker rmi ghcr.nju.edu.cn/xinnan-tech/mcp-endpoint-server:latest

# Start docker container
docker compose -f docker-compose.yml up -d
# View logs
docker logs -f mcp-endpoint-server
```

At this point, the logs will output something similar to:
```
======================================================
Interface URL: http://172.1.1.1:8004/mcp_endpoint/health?key=xxxx
=======The above URL is the MCP endpoint address, do not share with anyone============
```

Please copy the interface URL:

**Important: Since you're using Docker deployment, DO NOT use the above address directly!**

**Important: Since you're using Docker deployment, DO NOT use the above address directly!**

**Important: Since you're using Docker deployment, DO NOT use the above address directly!**

First copy the address and save it in a draft. You need to know your computer's local network IP. For example, if my computer's local IP is `192.168.1.1115`, then the original interface address:
```
http://172.1.1.1:8004/mcp_endpoint/health?key=xxxx
```
should be changed to:
```
http://192.168.1.1115:8004/mcp_endpoint/health?key=xxxx
```

After making the change, please access this interface directly using your browser. When the browser displays code similar to this, it means success:
```
{"result":{"status":"success","connections":{"tool_connections":0,"robot_connections":0,"total_connections":0}},"error":null,"id":null,"jsonrpc":"2.0"}
```

Please keep this `interface URL` safe, as you'll need it in the next step.

## Step 3: Configure the Management Console

Log in to the management console using an administrator account, click on `Parameter Dictionary` at the top, and select the `Parameter Management` function.

Then search for the parameter `server.mcp_endpoint`. At this point, its value should be `null`.
Click the modify button and paste the `interface URL` from the previous step into the `Parameter Value` field. Then save.

If you can save successfully, everything is going smoothly, and you can go to the AI agent to see the effects. If unsuccessful, it means the management console cannot access the MCP endpoint, most likely due to network firewall issues or incorrect local network IP configuration.

# How to Integrate a Simple MCP Function for the AI Agent, Such as Calculator Functionality

If the above steps went smoothly, you can enter AI agent management, click `Configure Role`, and on the right side of `Intent Recognition`, there's an `Edit Functions` button.

Click this button. In the popup page, at the bottom, there will be `MCP Endpoint`. Normally, it will display this AI agent's `MCP Endpoint Address`. Next, we'll extend this AI agent with calculator functionality based on MCP technology.

This `MCP Endpoint Address` is important - you'll need it shortly.

## Step 1: Download the MCP Calculator Project Code

Open the [calculator project](https://github.com/78/mcp-calculator) in your browser.

Once opened, find the green button labeled `Code` on the page, click it, and you'll see the `Download ZIP` button.

Click it to download the project source code archive. After downloading to your computer, extract it. The folder name might be `mcp-calculator-main`, which you need to rename to `mcp-calculator`. Next, we'll use the command line to enter the project directory and install dependencies:

```bash
# Enter project directory
cd mcp-calculator

conda remove -n mcp-calculator --all -y
conda create -n mcp-calculator python=3.10 -y
conda activate mcp-calculator

pip install -r requirements.txt
```

## Step 2: Launch

Before launching, first copy the MCP endpoint address from your AI agent in the management console.

For example, if my AI agent's MCP address is:
```
ws://192.168.4.7:8004/mcp_endpoint/mcp/?token=abc
```

Start by entering the command:

```bash
export MCP_ENDPOINT=ws://192.168.4.7:8004/mcp_endpoint/mcp/?token=abc
```

After entering this, start the program:

```bash
python mcp_pipe.py calculator.py
```

After startup, go back to the management console and click refresh on the MCP connection status. You'll then see the list of extended functions you've added.

