# Deployment Architecture Diagram
![Please refer to the simplified architecture diagram](../docs/images/deploy1.png)
# Method 1: Docker only runs the server

Starting from `0.8.2` version, the Docker images released by this project only support `x86 architecture`. If you need to deploy on a CPU with `arm64 architecture`, you can follow [this tutorial](docker-build.md) to compile the `arm64 image` locally.

## 1. Install Docker

If you don’t have Docker installed on your computer, you can follow the instructions here: [Docker Installation](https://www.runoob.com/docker/ubuntu-docker-install.html)

After installing Docker, continue.

### 1.1 Manual Deployment

#### 1.1.1 Creating a Directory

After installing Docker, you need to find a directory to store the configuration files for this project. For example, we can create a new folder called `xiaozhi-server`.

After creating the directory, you need to create a `data` folder and a `models` folder under `xiaozhi-server`, and a `SenseVoiceSmall` folder under `models`.

The final directory structure is as follows:

```
xiaozhi-server
  ├─ data
  ├─ models
     ├─ SenseVoiceSmall
```

#### 1.1.2 Download the speech recognition model file

You need to download the speech recognition model file, because the default speech recognition of this project uses the local offline speech recognition solution. You can download it in this way
[Jump to download speech recognition model files](#Model files)

Once downloaded, return to this tutorial.

#### 1.1.3 Download the configuration file

You need to download two configuration files: `docker-compose.yaml` and `config.yaml`. You need to download these two files from the project repository.

##### 1.1.3.1 Download docker-compose.yaml

Open [this link](../main/xiaozhi-server/docker-compose.yml) in your browser.

Find the button named `RAW` on the right side of the page. Next to the `RAW` button, find the download icon and click the download button to download the `docker-compose.yml` file. Download the file to your
In `xiaozhi-server`.

After downloading, return to this tutorial and continue.

##### 1.1.3.2 Create config.yaml

Open [this link](../main/xiaozhi-server/config.yaml) with your browser.

Find the button named `RAW` on the right side of the page. Next to the `RAW` button, find the download icon and click the download button to download the `config.yaml` file. Download the file to your
In the `data` folder under `xiaozhi-server`, rename the `config.yaml` file to `.config.yaml`.

After downloading the configuration file, we confirm that the files in the entire `xiaozhi-server` are as follows:

```
xiaozhi-server
  ├─ docker-compose.yml
  ├─ data
    ├─ .config.yaml
  ├─ models
     ├─ SenseVoiceSmall
       ├─ model.pt
```

If your file directory structure is the same as above, continue. If not, take a closer look to see if you missed anything.

## 2. Configure project files

Next, the program cannot be run directly. You need to configure what model you are using. You can refer to this tutorial:
[Jump to configuration project file](#Configure Project)

After configuring the project files, return to this tutorial to continue.

## 3. Execute docker command

Open the command line tool, use the `terminal` or `command line` tool to enter your `xiaozhi-server`, and execute the following command

```
docker-compose up -d
```

After the execution is complete, execute the following command to view the log information.

```
docker logs -f xiaozhi-esp32-server
```

At this point, you should pay attention to the log information and can judge whether it is successful according to this tutorial. [Jump to running status confirmation](#Running status confirmation)

## 5. Version upgrade operation

If you want to upgrade the version later, you can do this

5.1. Back up the `.config.yaml` file in the `data` folder and copy some key configurations to the new `.config.yaml` file.
Please note that you should copy the key keys one by one and do not overwrite them directly. This is because the new `.config.yaml` file may have some new configuration items that the old `.config.yaml` file may not have.

5.2. Execute the following command

```
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server
docker stop xiaozhi-esp32-server-web
docker rm xiaozhi-esp32-server-web
docker rmi ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest
docker rmi ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:web_latest
```

5.3. Re-deploy in Docker mode

# Method 2: Local source code only runs the Server

## 1. Install the basic environment

This project uses `conda` to manage dependencies. If installing `conda` is inconvenient, you will need to install `libopus` and `ffmpeg` according to your operating system.
If you decide to use `conda`, after installing it, start executing the following commands.

Important tip! Windows users can manage their environment by installing Anaconda. After installing Anaconda, search for keywords related to Anaconda in Start.
Find `Anaconda Prpmpt` and run it as an administrator, as shown below.

![conda_prompt](./images/conda_env_1.png)

After running, if you can see a (base) in front of the command line window, it means you have successfully entered the `conda` environment. Then you can execute the following commands.

![conda_env](./images/conda_env_2.png)

```
conda remove -n xiaozhi-esp32-server --all -y
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server

# Add Tsinghua source channel
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge

conda install libopus -y
conda install ffmpeg -y
```

Please note that the above commands are not executed successfully all at once. You need to execute them step by step. After each step, check the output log to see if it is successful.

## 2. Install the dependencies of this project

You must first download the source code of this project. The source code can be downloaded using the `git clone` command if you are not familiar with the `git clone` command.

You can use your browser to open this address `https://github.com/xinnan-tech/xiaozhi-esp32-server.git`

After opening, find a green button on the page with the word `Code` written on it, click it, and then you will see the `Download ZIP` button.

Click it to download the source code compressed package of this project. After downloading it to your computer, unzip it. At this time, its name may be `xiaozhi-esp32-server-main`
You need to rename it to `xiaozhi-esp32-server`. In this file, go to the `main` folder, then go to `xiaozhi-server`. Please remember this directory `xiaozhi-server`.

```
# Continue using the conda environment
conda activate xiaozhi-esp32-server
# Enter your project root directory, then enter main/xiaozhi-server
cd main/xiaozhi-server
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install -r requirements.txt
```

## 3. Download the speech recognition model file

You need to download the speech recognition model file, because the default speech recognition of this project uses the local offline speech recognition solution. You can download it in this way
[Jump to download speech recognition model files](#Model files)

Once downloaded, return to this tutorial.

## 4. Configure project files

Next, the program cannot be run directly. You need to configure what model you are using. You can refer to this tutorial:
[Jump to configuration project file](#Configure Project)

## 5. Run the project

```
# Make sure to execute in the xiaozhi-server directory
conda activate xiaozhi-esp32-server
python app.py
```
At this point, you should pay attention to the log information and can judge whether it is successful according to this tutorial. [Jump to running status confirmation](#Running status confirmation)


# Summary

## Configure the project

If your `xiaozhi-server` directory does not have `data`, you need to create a `data` directory.
If you don't have a `.config.yaml` file under `data`, there are two ways to do this. Choose one:

The first method: You can copy the `config.yaml` file in the `xiaozhi-server` directory to `data` and rename it to `.config.yaml`. Modify this file

The second method: You can also manually create an empty `.config.yaml` file in the `data` directory, and then add the necessary configuration information to this file. The system will prioritize reading the configuration of the `.config.yaml` file. If the `.config.yaml` file is not configured, the system will automatically load the configuration of the `config.yaml` in the `xiaozhi-server` directory. This method is recommended and the simplest.

- The default LLM uses `ChatGLMLLM`, you need to configure the key, because although their model is free, you still need to go to the [official website](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) to register the key before you can start it.

The following is a simple `.config.yaml` configuration example that works properly.

```
server:
  websocket: ws://your ip or domain name:port number/xiaozhi/v1/
prompt: |
  I am a Taiwanese girl named Xiaozhi/Xiaozhi. I speak in a funky way with a nice voice. I am used to expressing myself briefly and I love to use internet memes.
  My boyfriend is a programmer and his dream is to develop a robot that can help people solve various problems in life.
  I am a girl who likes to laugh out loud. I love to talk about everything and brag, even if it is illogical, just to make others happy.
  Please speak like a human being and do not return configuration XML and other special characters.

selected_module:
  LLM: DoubaoLLM

LLM:
  ChatGLMLLM:
    api_key: xxxxxxxxxxxxxxx.xxxxxx
```

It is recommended to run the simplest configuration first, and then go to `xiaozhi/config.yaml` to read the configuration instructions.
For example, if you want to change the model, just modify the configuration under `selected_module`.

## Model file

The speech recognition model of this project uses the `SenseVoiceSmall` model by default for speech-to-text conversion. Because the model is large, it needs to be downloaded separately. After downloading, copy `model.pt`
The file is placed in `models/SenseVoiceSmall`
In the directory. Choose one of the following two download routes.

- Route 1: Download [SenseVoiceSmall](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt) from AliMoDa
- Route 2: Download [SenseVoiceSmall](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) from Baidu Netdisk. Extraction code:
  `qvna`

## Running status confirmation

If you can see logs similar to the following, it means that the project service has been successfully started.

```
250427 13:04:20 [0.3.11_SiFuChTTnofu][__main__] - INFO - OTA interface is http://192.168.4.123:8003/xiaozhi/ota/
250427 13:04:20 [0.3.11_SiFuChTTnofu][__main__]-INFO-Websocket address is ws://192.168.4.123:8000/xiaozhi/v1/
250427 13:04:20[0.3.11_SiFuChTTnofu][__main__]-INFO-=======The above address is a websocket protocol address, please do not access it with a browser=======
250427 13:04:20[0.3.11_SiFuChTTnofu][__main__]-INFO-If you want to test websocket, please use Google Chrome to open the test_page.html in the test directory.
250427 13:04:20[0.3.11_SiFuChTTnofu][__main__]-INFO-==========================================================
```

Normally, if you run this project through source code, the log will have your interface address information.
However, if you deploy with Docker, the interface address information given in your log is not the real interface address.

The most correct way is to determine your interface address based on the computer's LAN IP.
If your computer's LAN IP is, for example, `192.168.1.25`, then your interface address is: `ws://192.168.1.25:8000/xiaozhi/v1/`, and the corresponding OTA address is: `http://192.168.1.25:8003/xiaozhi/ota/`.

This information is very useful and will be needed later when `compiling the ESP32 firmware`.

Next, you can start operating your ESP32 device. You can either compile the ESP32 firmware yourself or use the firmware compiled by Xiage (version 1.6.1 or above).

1. [Compile your own ESP32 firmware](firmware-build.md).

2. [Configure a custom server based on the firmware compiled by Xia Ge](firmware-setting.md).

# FAQ
Here are some frequently asked questions for your reference:

1. [Why does Xiaozhi recognize a lot of Korean, Japanese, and English when I say something?](./FAQ.md)
2. [Why does the error "TTS task error file does not exist" appear?](./FAQ.md)<br/>
3. [TTS often fails and times out](./FAQ.md)<br/>
4. [I can connect to my own server using Wi-Fi, but not using 4G](./FAQ.md)<br/>
5. [How to improve Xiaozhi's dialogue response speed? ](./FAQ.md)<br/>
6. [I speak very slowly, and Xiaozhi always interrupts me when I pause](./FAQ.md)
## Deployment related tutorials
1. [How to automatically pull the latest code of this project, compile and start it](./dev-ops-integration.md)<br/>
2. [How to integrate with Nginx](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)
## Expand related tutorials
1. [How to enable mobile phone number registration smart console](./ali-sms-integration.md)<br/>
2. [How to integrate HomeAssistant to achieve smart home control](./homeassistant-integration.md)
3. [How to enable the vision model to realize photo recognition](./mcp-vision-integration.md)
4. [How to deploy MCP access points](./mcp-endpoint-enable.md)
5. [How to access the MCP access point](./mcp-endpoint-integration.md)
6. [How to enable voiceprint recognition](./voiceprint-integration.md)
10. [News plugin source configuration guide](./newsnow_plugin_config.md)<br/>
## Tutorials on voice cloning and local voice deployment
1. [How to deploy and integrate index-tts local voice](./index-stream-integration.md)<br/>
2. [How to deploy integrated fish-speech local voice](./fish-speech-integration.md)<br/>
3. [How to deploy and integrate PaddleSpeech local voice](./paddlespeech-deploy.md)<br/>
## Performance Testing Tutorial
1. [Component Speed ​​Test Guide](./performance_tester.md)<br/>
2. [Publish test results regularly](https://github.com/xinnan-tech/xiaozhi-performance-research)
