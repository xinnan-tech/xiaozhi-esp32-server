# macOS 上的 Python Server-only 基础部署记录

本记录以 2026-10-09 的 `main` 提交 `a6cd755cf281f0e49ffbce489666acf09755de6c` 为基线，在独立分支 `docs/mac-server-deployment-20261009` 操作。只沿用仓库的 `FunASR`、`ChatGLMLLM` 和 `EdgeTTS`，不改变设备 Opus/WebSocket 音频协议。配置示例见 [mac-server-only.example.yaml](mac-server-only.example.yaml)。以下“结果”是该机器实测，不可当作其他 Mac 的保证。

## 2026-10-10 复测

本节在本地分支 `feature/child-agent-dialogue-20261010` 复核；它包含前一部署提交。因上游 GitHub 连接只有读取权限，尚未推送到 GitHub，也未创建 PR。

| 操作 | 本次实际结果 | 判定 |
|---|---|---|
| 环境 | macOS 14.1 arm64，仓库 `.venv` 为 Python 3.10.10；工作目录 Miniforge 提供 FFmpeg 9.0.2；设置 `DYLD_FALLBACK_LIBRARY_PATH` 后 `ctypes.CDLL('libopus.dylib')` 成功，FunASR、websockets、edge-tts 可导入 | 所选运行环境通过 |
| ASR 现有脚本 | `performance_tester_asr.py` 退出码 0；FunASR 对 4 个内置音频得到 `4/4 ✅`，平均 0.918 秒 | 通过 |
| TTS 现有脚本 | `performance_tester_tts.py` 退出码 0；EdgeTTS 三项检查均成功，汇总 `3 ✅` | 通过 |
| LLM 现有脚本 | `performance_tester_llm.py` 退出码 0，但所选 `ChatGLMLLM` 显示“未配置 api_key，已跳过”，没有真实模型回答 | **未通过** |
| 服务监听 | `app.py` 启动后，`lsof` 确认 `127.0.0.1:8000 LISTEN`；HTTP GET 返回 200；WebSocket 原生握手返回 `HTTP/1.1 101 Switching Protocols` | 启动和握手通过 |
| 停止服务 | 当前自动化沙箱拒绝向测试进程 PID 73812 发送 Ctrl+C 或 `kill -INT`（`operation not permitted`），复测时端口仍在监听 | **自动停止未通过**；在 Mac 终端执行 `kill -INT 73812`，然后用 `lsof -nP -iTCP:8000 -sTCP:LISTEN` 确认端口释放；PID 可能随进程变化 |

官方 `pip install -r requirements.txt` 仍因 `vosk==0.3.45` 在这台 Mac arm64/Python 3.10 上不可安装而**未通过**；本次没有改动官方依赖文件，也没有把临时依赖清单、模型文件、真实密钥或测试音频提交。

## 现有环境与安装结果

| 项目 | 实际结果 | 判定 |
|---|---|---|
| Git/分支 | 从上游 `main` 独立浅克隆，原工作区未覆盖；当前分支 `docs/mac-server-deployment-20261009` | 通过 |
| Python | macOS 14.1、arm64；系统有 Python 3.10.10 和 3.13.15；本仓库创建 `.venv`（3.10） | Python 环境通过；服务依赖另计 |
| FFmpeg / libopus | 初始均未检测到。`brew install ffmpeg opus` 因 Homebrew Git 锁和无可用 bottle 失败；随后在工作目录安装 Miniforge，以 `mamba install -c conda-forge ffmpeg libopus` 成功安装，`ffmpeg -version` 报 9.0.2；设置 `DYLD_FALLBACK_LIBRARY_PATH` 后，Python 3.10 用 `ctypes.CDLL("libopus.dylib")` 成功加载 | 系统音频库通过；完整服务另计 |
| 依赖 | 在 `.venv` 中按原始 `requirements.txt` 执行 `pip install -r`，PyPI 返回 `No matching distribution found for vosk==0.3.45`；工作目录临时清单只去掉未选用的 Vosk，其余依赖安装完成，`funasr==1.2.7`、`websockets==14.2`、`edge-tts==7.2.6` 可查 | 官方完整安装**未通过**；所选适配器依赖安装通过 |
| FunASR | 按上游部署文档下载 `models/SenseVoiceSmall/model.pt`（893 MB，SHA-256 `833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea`，与下载响应 `X-Linked-Etag` 相符；文件被 Git 忽略）。原 ASR 性能脚本把 WAV 容器字节当 PCM 输入，且多传一个参数，结果 `0/4`。本分支修正脚本后重跑，4 段内置 WAV 均识别出非空文本，汇总 `4/4 ✅`，平均 0.774 秒；另用适配器直接识别 `zh.mp3` 转成的 16 kHz 单声道 PCM，得到“开饭时间早上9点至下午5点。” | **通过**，仅证明本机 ASR 适配器和脚本 |
| LLM | 配置示例无真实密钥。原脚本收到三次 401 却错误汇总为 `3/3 ✅`；本分支修正异常和空回复判定。用假提供方验证 401/空回复均判失败；本地配置重跑显示 `ChatGLMLLM 未配置 api_key，已跳过` | **未通过**，无真实密钥与有效模型回答 |
| EdgeTTS | 上游 TTS 脚本实际生成连接测试及两段测试音频，汇总为 `EdgeTTS ✅ 正常`，均在被忽略的临时目录内 | 通过；仅验证服务端 TTS，不代表设备播放 |
| WebSocket | `app.py` 完成 FunASR 等模块初始化并监听 `127.0.0.1:8000`；HTTP GET 返回 200，原生 WebSocket 握手返回 `HTTP/1.1 101 Switching Protocols`；Ctrl+C 后端口释放 | 监听和握手通过；未验证设备会话/音频 |

## 官方依赖路径

上游 [Server-only 源码部署](Deployment.md) 推荐 Python 3.10，系统需 `libopus` 和 `ffmpeg`，然后在 `main/xiaozhi-server` 安装 `requirements.txt`。Mac 上不要把系统 Python 3.13 与这份固定依赖混用。当前 `requirements.txt` 固定 `torch==2.2.2`、`torchaudio==2.2.2`、`numpy==1.26.4`、`websockets==14.2` 等；依赖是否可用以安装与导入实测为准。当前 Mac arm64/Python 3.10 环境找不到 `vosk==0.3.45` 的可安装版本，所以不改仓库依赖文件，只在工作目录的临时清单中剔除未选用的 Vosk 以继续核验 FunASR/LLM/EdgeTTS。全套管理后台不属于本次 Server-only 范围。

## 本地配置

在仓库根目录执行：

```sh
mkdir -p main/xiaozhi-server/data
cp docs/mac-server-only.example.yaml main/xiaozhi-server/data/.config.yaml
```

`data/.config.yaml` 已被 `.gitignore` 忽略。它是**示例**，其中 `api_key` 占位符不能完成 LLM 测试；只在这个本地文件中填入你自己的密钥。FunASR 还需下载上游要求的 SenseVoiceSmall 模型文件；模型和密钥都不得提交。实体 ESP32 使用时，`127.0.0.1` 必须改为 Mac 局域网地址，并检查认证与网络边界。

## 启动、停止、日志与健康检查

从仓库根目录执行（系统库和依赖全部可用后）：

```sh
cd main/xiaozhi-server
# 若像本次一样将 FFmpeg/libopus 装在独立 Miniforge 中，先将其 bin/lib 放入当前终端环境。
# 具体路径以自己的安装位置为准；不需要修改全局 shell 配置。
export PATH="/path/to/miniforge3/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="/path/to/miniforge3/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
../../.venv/bin/python app.py
# 前台停止：按 Ctrl+C
```

前台进程日志直接显示在当前终端；程序还按 `config.yaml` 的 `log.log_dir`/`log.log_file` 写入 `tmp/server.log`。另一个终端可检查：

```sh
cd main/xiaozhi-server
tail -n 100 -f tmp/server.log
lsof -nP -iTCP:8000 -sTCP:LISTEN
curl -i --max-time 3 http://127.0.0.1:8000/
```

`curl` 的 HTTP 响应仅证明进程可达；**WebSocket 必须检查 101 升级**。在另一个终端运行以下不含密钥的握手：

```sh
python3.10 - <<'PY'
import base64, os, socket
key = base64.b64encode(os.urandom(16)).decode()
request = ("GET /xiaozhi/v1/ HTTP/1.1\r\nHost: 127.0.0.1:8000\r\n"
           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
with socket.create_connection(("127.0.0.1", 8000), timeout=3) as sock:
    sock.sendall(request.encode())
    print(sock.recv(1024).decode(errors="replace").split("\r\n", 1)[0])
PY
```

期望首行为 `HTTP/1.1 101 Switching Protocols`。这只验证监听和握手，**不等于 ASR/LLM/TTS 或 ESP32 全链路成功**。认证开关、代理和实际监听路径改变时需按服务端配置调整测试。

## 已有模型测试脚本

上游提供 `main/xiaozhi-server/performance_tester.py`，可交互选择 `performance_tester_asr`、`performance_tester_llm`、`performance_tester_tts`。先在被忽略的本地配置中完成模型/密钥设置，并提供测试音频。该脚本会调用真实提供方，可能联网和计费：

```sh
cd main/xiaozhi-server
../../.venv/bin/python performance_tester.py
```

也可在 `main/xiaozhi-server` 目录中单独运行上游脚本（需让脚本能导入项目的 `core` 包）：

```sh
export PYTHONPATH="$PWD"
../../.venv/bin/python performance_tester/performance_tester_asr.py
../../.venv/bin/python performance_tester/performance_tester_llm.py
../../.venv/bin/python performance_tester/performance_tester_tts.py
```

ASR 脚本从 `config/assets` 查找超过 300 KB 的 WAV 测试音频；本分支用 FFmpeg 转为适配器要求的 16 kHz 单声道 PCM，仓库内 4 个样本实际达到 `4/4`。LLM 缺真实密钥时不能判为通过。TTS 需产出实际音频文件才算通过；仅能导入适配器不算通过。记录每项脚本的退出码、摘要和实际输出，不提交任何儿童录音、日志密钥或生成音频。

**判定以真实结果为准，不以脚本退出码或单独的汇总“✅”为准。**修复前 ASR 退出码为 0，但 `0/4`；LLM 首次使用无效占位符时收到 401，汇总却显示 `3/3 ✅`。本分支修正了这两处性能脚本问题。本示例的占位符含“你的”，让脚本跳过无密钥的 LLM。

## 尚需人工完成

1. 在被 Git 忽略的 `main/xiaozhi-server/data/.config.yaml` 中填入自己申请的真实 LLM API Key，确认提供方可用、配额和费用，然后重跑 LLM 性能脚本；目前状态必须保留为**未通过**。
2. 接入真实 ESP32-S3、麦克风与扬声器，在局域网正确配置服务端地址，并验证语音输入、识别、模型回答、合成、播放的完整循环；本次仅验证本机 WebSocket 握手，未做端到端设备测试。
3. 如需完整官方依赖安装或启用 Vosk，在适配 macOS arm64 的 Python/包源环境中解决 `vosk==0.3.45` 分发问题并重跑完整 `pip install -r requirements.txt`；当前该项**未通过**。
