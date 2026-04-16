# xiaozhi-esp32-server 项目环境搭建与启动完整操作手册

# 前言

本文档为 xiaozhi-esp32-server 项目的完整环境搭建、依赖安装及项目启动操作指南，全程适配 Windows 系统 + Conda 环境，已规避所有已遇到的报错（如 DLL 加载失败、Opus 库找不到等），按步骤执行即可顺利启动项目。

⚠️ 关键提醒：全程若出现 *Error while loading conda entry point: conda-libmamba-solver (DLL load failed...)* 红色提示，直接无视，不影响任何操作和项目运行。

# 一、环境准备（前提）

已安装 Miniconda（或 Anaconda），打开 **Anaconda Prompt**（以管理员身份运行更佳），进入默认 base 环境。

# 二、Conda 环境创建与激活

创建项目专属 Conda 环境（Python 3.10），确保环境干净无冲突，步骤如下：

```bash
# 1. 删除旧环境（若存在，确保环境干净重建）
conda remove -n xiaozhi-esp32-server --all -y

# 2. 创建新环境（指定 Python 3.10，强制使用稳定经典求解器，规避报错）
conda create -n xiaozhi-esp32-server python=3.10 -y --solver=classic

# 3. 激活项目专属环境（后续所有操作均在此环境下执行）
conda activate xiaozhi-esp32-server
```

执行完成后，终端提示符会变为 *(xiaozhi-esp32-server)*，表示环境激活成功。

为确保当前项目环境始终使用经典求解器，避免报错，执行以下命令（仅对当前环境生效，不影响全局配置）：

```bash
conda config --set solver classic --env
```

# 三、镜像配置与核心依赖安装

## 3.1 配置清华镜像（加速依赖下载）

```bash
# 添加清华源通道（优先使用国内镜像，避免下载缓慢）
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
# 显示下载通道地址（可选，验证镜像配置成功）
conda config --set show_channel_urls yes
```

## 3.2 安装项目必需底层依赖

安装 Opus 音频编解码库、FFmpeg 工具（项目语音功能必需，避免后续报错）：

```bash
conda install libopus ffmpeg -y --solver=classic
```

# 四、切换到项目目录

项目路径：**D:\work_space\xiaozhi-esp32-server**，按以下命令切换到项目启动目录：

```bash
# 1. 切换到项目所在盘符（D盘，无需修改）
D:

# 2. 进入项目根目录（路径固定，直接复制执行）
cd D:\work_space\xiaozhi-esp32-server\main/xiaozhi-server

```

执行完成后，终端路径会显示为*(xiaozhi-esp32-server) D:\work_space\xiaozhi-esp32-server\main\xiaozhi-server*，表示目录切换成功。

# 五、Python 依赖安装与项目启动

## 5.1 配置 pip 镜像（加速 Python 依赖下载）

```bash
# 配置阿里云 pip 源，避免依赖下载失败或缓慢
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

## 5.2 安装项目所有 Python 依赖

安装 requirements.txt 中指定的所有 Python 依赖（项目运行必需）：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 5.3 修复 Opus 库调用报错（必执行）

解决“Could not find Opus library”报错，强制重装 Python 调用 Opus 库的工具：

```bash
pip install opuslib-next --force-reinstall
```

## 5.4 启动项目

所有准备工作完成后，执行以下命令启动项目：

```bash
python app.py
```

✅ 启动成功标志：终端无红色 Exception 报错，显示本地 IP 地址（可用于连接 ESP32 设备）。

# 六、常见问题与注意事项

- 问题1：执行 conda 命令时出现 DLL 加载失败提示 → 直接无视，不影响操作。

- 问题2：启动项目时报“Could not find Opus library” → 重新执行步骤 5.3（强制重装 opuslib-next）。

- 问题3：cd 命令无法切换目录 → 检查路径是否正确，确保项目路径为 D:\work_space\xiaozhi-esp32-server，先切换盘符再执行 cd 命令。

- 注意：所有命令需按文档顺序执行，不可跳过步骤；若环境异常，可重新执行“第二步”重建环境。

# 七、总结

本手册涵盖从 Conda 环境创建、镜像配置、依赖安装，到目录切换、项目启动的完整流程，适配你的项目路径和环境，全程规避已遇到的所有报错，可直接作为后续重复启动项目的参考指南。
> （注：文档部分内容可能由 AI 生成）