# 部署指南

本项目支持 **x86** 和 **arm64** 架构，可运行于国产操作系统。

## 方式一：快速部署（推荐）

### 1. 安装 Docker

如果未安装 Docker，可参考 [Docker 安装教程](https://www.runoob.com/docker/ubuntu-docker-install.html)。

### 2. 创建项目目录

选择一个空目录作为 **项目目录**。

### 3. 下载配置文件

访问 [config.yaml](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/config.yaml)，点击 `RAW` 旁的下载按钮，保存到 **项目目录**。

### 4. 运行 Docker

打开终端，`cd` 进入 **项目目录**，执行：

```sh
docker run -d --name xiaozhi-esp32-server --restart always --security-opt seccomp:unconfined \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/opt/xiaozhi-esp32-server/config.yaml \
  ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

### 5. 确认运行状态

```sh
docker ps  # 查看容器状态
docker logs -f xiaozhi-esp32-server  # 查看日志
```

## 方式二：使用 Docker Compose 部署

### 1. 创建 `docker-compose.yml`
在 `项目目录` 下创建 `docker-compose.yml` 文件，内容如下：

```yaml
version: '3'
services:
  xiaozhi-esp32-server:
    image: ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
    container_name: xiaozhi-esp32-server
    restart: always
    security_opt:
      - seccomp:unconfined
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/opt/xiaozhi-esp32-server/config.yaml
```

### 2. 启动服务
```sh
docker-compose up -d
```

### 3. 确认运行状态
```sh
docker-compose ps
docker-compose logs -f
```

### 4. 停止和删除容器
```sh
docker-compose down
```

### 5. 版本升级

#### 备份配置文件
```sh
cp config.yaml config_backup.yaml
```

#### 更新 Docker 镜像
```sh
docker-compose pull
docker-compose down
docker-compose up -d
```


## 方式三：源码部署（免环境部署/可修改代码）

### 1. 下载源码

```sh
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server.git
cd xiaozhi-esp32-server
```

或手动下载 [ZIP 包](https://github.com/xinnan-tech/xiaozhi-esp32-server/archive/refs/heads/main.zip)，解压后重命名为 `xiaozhi-esp32-server`。

## 2.运行docker

修改完配置后，打开命令行工具，`cd`进入到你的项目目录下，执行以下命令

```sh
docker run -it --name xiaozhi-env --restart always --security-opt seccomp:unconfined \
  -p 8000:8000 \
  -p 8002:8002 \
  -v ./:/app \
  kalicyh/poetry:v3.10_latest
```

然后就和正常开发一样了

## 3.安装依赖

在刚刚的打开的终端运行

```sh
poetry install --no-root
```

```sh
apt-get update
apt-get install -y --no-install-recommends libopus0 ffmpeg
```

速度慢可以尝试使用清华镜像

```sh
echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list
echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list
echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list
echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list
apt-get update
apt-get install -y --no-install-recommends libopus0 ffmpeg
```

## 4.运行项目

```sh
poetry run python app.py
```

## 方式三：本地运行（适用于开发）

### 1. 安装环境

```sh
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server
```

#### Mac/Windows:

```sh
conda install conda-forge::libopus conda-forge::ffmpeg
```

#### Ubuntu:

```sh
apt-get install libopus0 ffmpeg
```

### 2. 下载源码 & 安装依赖

```sh
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server.git
cd xiaozhi-esp32-server
pip install -r requirements.txt
```

### 3. 运行项目

```sh
python app.py
```

## 版本升级

```sh
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server
docker rmi ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

然后重新按照 **方式一** 或 **方式二** 运行 Docker。

## 重要配置

修改 `config.yaml` 以适配不同 LLM 和 TTS 组件。

示例：

```yaml
selected_module:
  ASR: FunASR
  VAD: SileroVAD
  LLM: ChatGLMLLM
  TTS: EdgeTTS
```

如需使用 `Dify` 或 `DeepSeekLLM`，修改 `LLM` 部分并填写密钥。

## 模型文件下载

语音转文字默认使用 `SenseVoiceSmall`，需下载 `model.pt` 并存放至 `model/SenseVoiceSmall` 目录。

- [阿里魔塔下载](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt)
- [百度网盘下载](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) 提取码：`qvna`

---

如遇问题，可参考 `docker logs -f xiaozhi-esp32-server` 进行排查。

**至此，部署完成！** 🚀


