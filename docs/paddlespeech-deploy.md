# PaddleSpeechTTS集成xiaozhi服务

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
#请根据Paddle官方支持的python版本建立环境  ```https://www.paddlepaddle.org.cn/install```
conda create -n paddle_env python=3.10 -y
conda activate paddle_env
```
### 3.进入paddlespeech目录
```bash
cd PaddleSpeech
```
### 4.安装paddlespeech
```bash
pip install pytest-runner -i https://pypi.tuna.tsinghua.edu.cn/simple

#以下命令使用任意一个
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
pip install paddlespeech -i https://pypi.tuna.tsinghua.edu.cn/simple
```
### 5.使用命令自动下载语音模型
```bash
paddlespeech tts --input "你好，这是一次测试"
```
此步骤会自动下载模型缓存至本地 .paddlespeech/models 目录

### 6.修改tts_online_application.yaml配置
参考目录 ```"PaddleSpeech\demos\streaming_tts_server\conf\tts_online_application.yaml"```
选择```tts_online_application.yaml```文件用编辑器打开，设置```protocol```为```websocket```

### 7.启动服务
```yaml
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

## 三、修改小智的配置文件
### 1.```main/xiaozhi-server/core/providers/tts/paddle_speech.py```

### 2.```main/xiaozhi-server/data/.config.yaml```
使用单模块部署
```yaml
selected_module:
  TTS: PaddleSpeechTTS
TTS:
  PaddleSpeechTTS:
      type: paddle_speech
      protocol: websocket 
      url:  ws://127.0.0.1:8092/paddlespeech/tts/streaming  # TTS 服务的 URL 地址，指向本地服务器 [websocket默认ws://127.0.0.1:8092/paddlespeech/tts/streaming]
      spk_id: 0  # 发音人 ID，0 通常表示默认的发音人
      sample_rate: 24000  # 采样率 [websocket默认24000，http默认0 自动选择]
      speed: 1.0  # 语速，1.0 表示正常语速，>1 表示加快，<1 表示减慢
      volume: 1.0  # 音量，1.0 表示正常音量，>1 表示增大，<1 表示减小
      save_path:   # 保存路径
```
### 3.启动xiaozhi服务
```py
python app.py
```
打开test目录下的test_page.html，测试连接和发送消息时paddlespeech端是否有输出日志

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
