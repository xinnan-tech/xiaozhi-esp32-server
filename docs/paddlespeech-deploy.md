# PaddleSpeechTTS集成xiaozhi服务

## 重点说明
- 优点：本地离线部署、速度快
- 缺点：截止2025年9月25日，默认的模型是中文模型，不支持英文转语音。如果含英文会发不出声音，如需同时支持中英文需要自己训练。

## 一、基础环境要求
操作系统：Windows / Linux / WSL 2

Python 版本：3.9以上（请根据Paddle官方教程调整）

Paddle 版本：官方最新版本   ```https://www.paddlepaddle.org.cn/install```

依赖管理工具：conda 或 venv

## 二、启动paddlespeech服务
### 1.从paddlespeech官方仓库拉取源码
```bash 
git clone https://github.com/PaddlePaddle/PaddleSpeech.git
```
### 2.建立虚拟环境
```bash

conda create -n paddle_env python=3.10 -y
conda activate paddle_env
```
### 3.安装paddle
因CPU架构、GPU架构不同，请根据Paddle官方支持的python版本建立环境  
```
https://www.paddlepaddle.org.cn/install
```

### 4.进入paddlespeech目录
```bash
cd PaddleSpeech
```
### 5.安装paddlespeech
```bash
pip install pytest-runner -i https://pypi.tuna.tsinghua.edu.cn/simple

#以下命令使用任意一个
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
pip install paddlespeech -i https://pypi.tuna.tsinghua.edu.cn/simple
```
### 6.使用命令自动下载语音模型
```bash
paddlespeech tts --input "你好，这是一次测试"
```
此步骤会自动下载模型缓存至本地 .paddlespeech/models 目录

### 7.修改tts_online_application.yaml配置
参考目录 ```"PaddleSpeech\demos\streaming_tts_server\conf\tts_online_application.yaml"```
Linux / WSL 2 用正斜杠写法：```"PaddleSpeech/demos/streaming_tts_server/conf/tts_online_application.yaml"```
选择```tts_online_application.yaml```文件用编辑器打开，设置```protocol```为```websocket```

### 8.启动服务
```bash
paddlespeech_server start --config_file ./demos/streaming_tts_server/conf/tts_online_application.yaml
#官方默认启动命令：
paddlespeech_server start --config_file ./conf/tts_online_application.yaml
```
请根据你的```tts_online_application.yaml```的实际目录来启动命令，看到如下日志即启动成功
```
Prefix dict has been built successfully.
[2025-08-07 10:03:11,312] [   DEBUG] __init__.py:166 - Prefix dict has been built successfully.
INFO:     Started server process [2298]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8092 (Press CTRL+C to quit)
```

## 三、配置小智服务
### 1. 无需修改代码（provider 已内置于 main/xiaozhi-server/core/providers/tts/paddle_speech.py）

### 2.新建 `main/xiaozhi-server/data/.config.yaml`

`main/xiaozhi-server/data/` 目录不在仓库里，是被 `.gitignore` 忽略掉的，所以第一次用要先把它建出来，再在里面新建 `.config.yaml` 文件（在仓库根目录执行，上面的 `cd PaddleSpeech` 之后当前目录还停在 PaddleSpeech 源码目录里）：

```bash
mkdir -p main/xiaozhi-server/data
```

这个文件是必需的，少了它小智服务起不来，会直接报错退出。

使用单模块部署
```yaml
selected_module:
  TTS: PaddleSpeechTTS
TTS:
  PaddleSpeechTTS:
      type: paddle_speech
      protocol: websocket  # 当前仅支持 websocket
      url:  ws://127.0.0.1:8092/paddlespeech/tts/streaming  # TTS 服务的 URL 地址，指向本地服务器 [websocket默认ws://127.0.0.1:8092/paddlespeech/tts/streaming]
      spk_id: 0  # 发音人 ID，0 通常表示默认的发音人
      speed: 1.0  # 语速，1.0 表示正常语速，>1 表示加快，<1 表示减慢
      volume: 1.0  # 音量，1.0 表示正常音量，>1 表示增大，<1 表示减小
      save_path:   # 保存路径
```
采样率固定 24000，provider 内部写死，配置里不用写这一项。

### 3.启动xiaozhi服务

小智服务用**另一个** Python 环境，不要用前面给 PaddleSpeech 建的 `paddle_env` —— 那个环境里装的是 PaddleSpeech 自己那套依赖，版本由它决定，跟本项目锁定的版本不一定一致（`paddlespeech` 对 numpy 没写版本上限，装进去的 numpy 未必是本项目要的那个）。本项目推荐的 Python 版本和依赖版本写在 `main/xiaozhi-server/requirements.txt` 里（文件开头写着推荐 python3.10，另外锁了 torch 2.2.2、numpy 1.26.4）。

先建环境、装依赖（在仓库根目录执行）：
```bash
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server
cd main/xiaozhi-server
pip install -r requirements.txt
```

然后在 `main/xiaozhi-server` 目录下启动（目录不能换：provider 是按相对路径 `core/providers/tts/` 找的，见 `core/utils/tts.py:35`）：
```bash
# 上一段已经 cd 到 main/xiaozhi-server 了，这段不用再 cd
# 如果是另开的新终端，先 cd main/xiaozhi-server 再执行
python app.py
```

要验证语音合成的实际输出，另开一个终端，在仓库根目录下跑数字人页面（这套代码另有一份依赖清单，在 `main/digital-human/wakeword_runtime/requirements.txt` 里，缺了会报缺包；唤醒词那部分还要 numpy —— `core/detector.py:7` 和 `core/microphone.py:4` 在模块顶层就 import numpy，用上面建的 `xiaozhi-esp32-server` 跑的话 numpy 已经在里面，不会有这个问题）：
```bash
cd main/digital-human
python start.py
```

打开`http://127.0.0.1:8006/index.html`，测试连接和发送消息时paddlespeech端是否有输出日志

输出日志参考：
```
INFO:     127.0.0.1:44312 - "WebSocket /paddlespeech/tts/streaming" [accepted]
INFO:     connection open
[2025-08-07 11:16:33,355] [    INFO] - sentence: 哈哈，怎么突然找我聊天啦？
[2025-08-07 11:16:33,356] [    INFO] - The durations of audio is: 2.4625 s
[2025-08-07 11:16:33,356] [    INFO] - first response time: 0.1143045425415039 s
[2025-08-07 11:16:33,356] [    INFO] - final response time: 0.4777836799621582 s
[2025-08-07 11:16:33,356] [    INFO] - RTF: 0.19402382942625715
[2025-08-07 11:16:33,356] [    INFO] - Other info: front time: 0.06514096260070801 s, first am infer time: 0.008037090301513672 s, first voc infer time: 0.04112648963928223 s,
[2025-08-07 11:16:33,356] [    INFO] - Complete the synthesis of the audio streams
INFO:     connection closed

```
