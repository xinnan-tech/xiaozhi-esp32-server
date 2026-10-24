# Python 端安装启动说明

> 适用目录：`main/xiaozhi-server`
> 安装方式：项目内 Python 虚拟环境（`.venv`），不使用 conda
> 验证环境：Windows + Python 3.11.3 + ffmpeg 9.0.2 + libopus 1.3.1

## 0. 环境与端口

| 项目 | 值 |
| --- | --- |
| Python | 3.11.3（`py -3.11` 启动器；项目推荐 3.10，3.11 实测可用） |
| 虚拟环境 | `main/xiaozhi-server/.venv` |
| ffmpeg | 9.0.2（Gyan 构建） |
| libopus | 1.3.1（`opus.dll`） |
| WebSocket | 8000 |
| HTTP（OTA / 视觉分析） | 8003 |
| 关键依赖 | torch 2.2.2、torchaudio 2.2.2、funasr 1.4.16、numpy 1.26.4、websockets 14.2 |

## 1. 创建虚拟环境

```powershell
cd main\xiaozhi-server
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

若提示“禁止运行脚本”，先在当前窗口放行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

升级打包工具（可选，建议做）：

```powershell
python -m pip install --upgrade pip setuptools wheel -i https://mirrors.aliyun.com/pypi/simple/
```

## 2. 安装 ffmpeg

```powershell
winget install --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
```

安装后把 `ffmpeg.exe`、`ffprobe.exe` 复制到虚拟环境的 `Scripts` 目录，避免 IDE 或子进程拿到的 PATH 里没有 ffmpeg：

```powershell
$bin = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin" -Recurse -Filter ffmpeg.exe | Select-Object -First 1
Copy-Item $bin.FullName .venv\Scripts\
Copy-Item (Join-Path $bin.DirectoryName 'ffprobe.exe') .venv\Scripts\
.\.venv\Scripts\ffmpeg.exe -version
```

> winget 安装 ffmpeg 时已自动把它加入系统 PATH，正常启动可直接找到。若只想使用复制到 `.venv\Scripts` 的这份，需要把该目录加入 PATH（见 4.1 节）；否则启动检查 `check_ffmpeg_installed()` 会报 ffmpeg 无法运行，pydub 也会打印 `Couldn't find ffmpeg or avconv` 警告。

## 3. 安装 Python 依赖

```powershell
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --timeout 180
```

- torch 2.2.2 体积较大，首次安装耗时较长属正常现象；超时可重复执行（pip 有缓存）。
- 本项目固定 `transformers<5`，不要手动升级到 transformers 5.x（会导致 torch 2.2.2 不可用，本地 ASR 无法加载）。

## 4. 安装 libopus（Windows 必需）

venv 里无法用 conda 安装 libopus，而 `opuslib_next` 在 Windows 上会查找 PATH 中的 `opus.dll`。这里从 conda-forge 提取官方编译好的 DLL：

```powershell
$d = "$env:TEMP\opus_dl"
New-Item -ItemType Directory -Path $d -Force | Out-Null
Invoke-WebRequest -UseBasicParsing `
  'https://conda.anaconda.org/conda-forge/win-64/libopus-1.3.1-h8ffe710_1.tar.bz2' `
  -OutFile "$d\libopus.tar.bz2"

# Windows 自带 tar 不支持 bz2，用 Python 解压
.\.venv\Scripts\python.exe -c "import tarfile,os;d=os.path.join(os.environ['TEMP'],'opus_dl');tarfile.open(os.path.join(d,'libopus.tar.bz2')).extractall(d)"

Copy-Item "$d\Library\bin\opus.dll" .venv\Scripts\
```

验证：

```powershell
python -c "from opuslib_next import Encoder; Encoder(24000,1,2049); print('opus ok')"
```

> `opuslib_next` 在 Windows 下只用 `ctypes.util.find_library("opus")` 按 **PATH** 查找 `opus.dll`，不会查 `python.exe` 所在目录。因此必须把 `.venv\Scripts` 加入 PATH，否则会报 `Exception: Could not find Opus library`。

**4.1 把 `.venv\Scripts` 加入 PATH（Windows）**

方式一：图形界面（推荐，永久生效）

1. `Win+R` → 输入 `sysdm.cpl` → 「高级」→「环境变量」
2. 在「用户变量」中选中 `Path` → 「编辑」→「新建」，填入：
   `D:\工作空间\code\xiaozhi\xiaozhi-esp32-server\main\xiaozhi-server\.venv\Scripts`
3. 逐级「确定」；已打开的终端、IDEA 需要重启才会读到新 PATH

方式二：PowerShell 永久写入用户 Path

```powershell
$dir = 'D:\工作空间\code\xiaozhi\xiaozhi-esp32-server\main\xiaozhi-server\.venv\Scripts'
$old = [Environment]::GetEnvironmentVariable('Path','User')
[Environment]::SetEnvironmentVariable('Path', "$old;$dir", 'User')
```

系统级（所有用户）需管理员权限，把 `'User'` 换成 `'Machine'`。

方式三：只在当前窗口临时生效

```powershell
$env:PATH = 'D:\工作空间\code\xiaozhi\xiaozhi-esp32-server\main\xiaozhi-server\.venv\Scripts;' + $env:PATH
```

验证（需在新开的终端中执行）：

```powershell
where.exe opus.dll
python -c "import ctypes.util; print(ctypes.util.find_library('opus'))"
```

第二条输出 `...\.venv\Scripts\opus.dll` 即配置成功；同时 `where.exe ffmpeg` 也能输出路径，说明 ffmpeg 同样可用。

**IDEA / PyCharm 运行配置**

1. `Run` → `Edit Configurations...`
2. 选中运行 `app.py` 的 Python 配置
3. 找到 `Environment variables`，点击右侧输入框，填：

   ```
   PATH=D:\工作空间\code\xiaozhi\xiaozhi-esp32-server\main\xiaozhi-server\.venv\Scripts;$PATH$
   ```

   `$PATH$` 会展开为当前的系统 PATH（JetBrains 的宏语法，保留原有 PATH，避免 ffmpeg 等命令丢失）。
4. `Apply` → `OK`，再运行。

如果该版本不支持 `$PATH$`，可改为在 IDEA 底部的 Terminal 里先执行 `.\.venv\Scripts\Activate.ps1`，再用 `python app.py` 启动。

## 5. 配置 data/.config.yaml

`config/config_loader.py` 会直接读取 `data/.config.yaml`，文件不存在会报 `FileNotFoundError`；文件存在但完全为空（YAML 解析为 `None`）会报 `AttributeError: 'NoneType' object has no attribute 'get'`。因此至少要写入 `{}`。

```powershell
New-Item -ItemType Directory -Path data -Force | Out-Null
Set-Content data\.config.yaml "{}" -Encoding utf8
```

两种配置模式：

**A. 本地配置模式（当前使用，不依赖 Java 端）**

保持 `data/.config.yaml` 为 `{}`，直接使用 `config.yaml`：

- 模型选择在 `selected_module`（默认：`FunASR` / `ChatGLMLLM` / `EdgeTTS` / `SileroVAD` / `nomem` / `function_call`）
- LLM 密钥需在 `config.yaml` 的 `LLM` 段填写真实 `api_key`

**B. 智控台配置模式（需先启动 manager-api + manager-web）**

```yaml
manager-api:
  url: http://127.0.0.1:8002/xiaozhi
  secret: 智控台「参数管理」里 server.secret 的值
```

写入后启动时会从 Java 端拉取模型配置，`config.yaml` 中的模型配置不再生效。

- 判断是否走了 manager-api：启动时会打印 `成功从manager-api获取配置` 及脱敏后的完整配置（`secret`、`api_key`、`private_key` 等显示为 `***`）；同时调用 `POST /config/server-base`。日志里**不再打印**“OTA接口是 http://…:8003/…”，但 WebSocket 地址仍会打印（OTA 由 manager-api 的 8002 提供）。
- `secret` 不能保留占位符（含“你”会直接报错）；每次从零部署 `server.secret` 都会变化。
- manager-api 必须先启动，否则 Python 端会重试 6 次（间隔 10s）后报 `Failed to fetch server config from API`。
- 监听端口等仍以本地为准：如需固定，可参照 `config_from_api.yaml` 一并写上 `server` 段的 `ip` / `port` / `http_port` / `vision_explain`。
- 本地模式下 `config.yaml` 里的 LLM/ASR/TTS 选择与密钥在 API 模式下失效，必须在智控台「模型配置」里配好，否则设备连接后会报错。

## 6. 下载本地 ASR 模型（FunASR / SenseVoiceSmall）

本地模式下 ASR 使用 `models/SenseVoiceSmall`。缺少 `model.pt` 时服务仍能启动，但识别结果是乱码，必须补齐：

```powershell
.\.venv\Scripts\modelscope.exe download --model iic/SenseVoiceSmall model.pt --local_dir models/SenseVoiceSmall
```

约 936 MB。下载完成后目录应包含 `model.pt`、`config.yaml`、`configuration.json` 等文件。

可选验证：

```powershell
python -c "from funasr import AutoModel; m=AutoModel(model='models/SenseVoiceSmall',disable_update=True,hub='hf'); print(m.generate(input='models/SenseVoiceSmall/example/zh.mp3')[0]['text'])"
```

## 7. 启动

```powershell
cd main\xiaozhi-server
.\.venv\Scripts\Activate.ps1
python app.py
```

启动成功的日志（地址随本机局域网 IP 变化）：

```
OTA接口是          http://192.168.x.x:8003/xiaozhi/ota/
视觉分析接口是     http://192.168.x.x:8003/mcp/vision/explain
Websocket地址是    ws://192.168.x.x:8000/xiaozhi/v1/
server listening on 0.0.0.0:8000
```

验证：

```powershell
netstat -ano | findstr ":8000"
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8003/xiaozhi/ota/).StatusCode   # 期望 200
```

停止：在运行窗口按 `Ctrl+C`。

> WebSocket 地址不能用浏览器直接打开；浏览器端对话测试请启动 `main/digital-human`（<http://127.0.0.1:8006/index.html>）。

## 8. 语音对话前提

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| ASR（本地 FunASR） | 需模型 | 按第 6 节下载 `model.pt`，否则识别乱码 |
| LLM | **需配置密钥** | `config.yaml` 默认是占位符（如 `你的chat-glm web key`），日志会报 `LLM 的 API key 未设置`，服务能启动但不会回复 |
| TTS（EdgeTTS） | 开箱可用 | 无需密钥 |
| VAD（Silero） | 开箱可用 | 模型已在仓库内 |
| 设备接入地址 | 按需配置 | 智控台模式下要在「参数管理」填 `server.websocket`、`server.ota`，用局域网 IP，不能填 `127.0.0.1` |

## 9. 本次安装遇到的问题与处理

| 问题 | 现象 | 处理 |
| --- | --- | --- |
| `data/.config.yaml` 为空文件 | `AttributeError: 'NoneType' object has no attribute 'get'` | 写入 `{}`，不要留纯空文件 |
| 未安装 ffmpeg | `ffmpeg 无法正常运行` / pydub 警告 | `winget install Gyan.FFmpeg`，并把 exe 复制到 `.venv\Scripts` |
| 缺少 libopus | `Could not find Opus library` | 从 conda-forge 取 `libopus-1.3.1`，`opus.dll` 放入 `.venv\Scripts`，并把该目录加入 PATH（见 4.1 节） |
| `where opus.dll` 能找到，但运行仍报 `Could not find Opus library` | 当前进程的 PATH 是改 PATH 之前继承的旧值（终端/IDE 未重启） | 关闭并重启终端与 IDE；在报错的那个进程里打印 `os.environ['PATH']` 确认是否包含 `.venv\Scripts` |
| 缺少 ASR 权重 | SenseVoice 推理输出乱码 | 用 modelscope 下载 `model.pt` 到 `models/SenseVoiceSmall` |
| LLM 密钥为占位符 | 启动日志 ERROR：`LLM 的 API key 未设置` | 在 `config.yaml` 填真实密钥，或改用智控台配置模式 |
| 端口被占用 | 启动报地址占用 | `netstat -ano \| findstr :8000` 后结束对应进程 |

## 10. 常用命令速查

```powershell
# 进入环境
cd main\xiaozhi-server; .\.venv\Scripts\Activate.ps1

# 启动 / 停止
python app.py            # Ctrl+C 停止

# 检查端口
netstat -ano | findstr ":8000"

# 重新安装依赖
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --timeout 180
```
