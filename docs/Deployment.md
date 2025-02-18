# 方式一：docker快速部署

docker镜像已支持x86架构、arm64架构的CPU，支持在国产操作系统上运行。

## 1. 安装docker

如果您的电脑还没安装docker，可以按照这里的教程安装：[docker安装](https://www.runoob.com/docker/ubuntu-docker-install.html)

## 2. 创建目录

安装完后，你需要为这个项目找一个安放配置文件的目录，我们暂且称它为`项目目录`，这个目录最好是一个新建的空的目录。

## 3. 下载配置文件

用浏览器打开[这个链接](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/config.yaml)。

在页面的右侧找到名称为`RAW`按钮，在`RAW`按钮的旁边，找到下载的图标，点击下载按钮，下载`config.yaml`文件。 把文件下载到你的
`项目目录`。

## 4.[跳转到配置项目文件](#配置项目)

## 5. 执行docker命令

打开命令行工具，`cd` 进入到你的`项目目录`，执行以下命令

```
#如果你是linux，执行
ls
#如果你是windows，执行
dir
```

如果你能看到`config.yaml`文件，确确实实进入到了`项目目录`，接着执行以下命令：

```
docker run -d --name xiaozhi-esp32-server --restart always --security-opt seccomp:unconfined -p 8000:8000 -v $(pwd)/config.yaml:/opt/xiaozhi-esp32-server/config.yaml ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

## 6.[跳转到运行状态确认](#运行状态确认)

## [跳转到版本升级操作](#版本升级操作)

# 方式二：借助docker环境运行部署（仅限开发人员/小白勿用）

## 1.克隆项目

## 2.[跳转到下载语音识别模型文件](#模型文件)

## 3.[跳转到配置项目文件](#配置项目)

## 4.运行docker

修改完配置后，打开命令行工具，`cd`进入到你的项目目录下，执行以下命令

```sh
docker run -it --name xiaozhi-env --restart always --security-opt seccomp:unconfined \
  -p 8000:8000 \
  -p 8002:8002 \
  -v ./:/app \
  ccr.ccs.tencentyun.com/kalicyh/poetry:v3.10_latest
```

然后就和正常开发一样了

## 5.安装依赖

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

## 6.运行项目

```sh
poetry run python app.py
```

# 方式三：本地源码运行

## 1.安装基础环境

本项目使用`conda`管理依赖环境，安装好后，开始执行以下命令。

```
conda remove -n xiaozhi-esp32-server --all -y
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server
```

执行以上命令后， 如果你的电脑是Windows或Mac，执行下面的语句：

```
conda activate xiaozhi-esp32-server
conda install conda-forge::libopus
conda install conda-forge::ffmpeg
```

如果你的电脑是ubuntu，执行下面的语句：

```
apt-get install libopus0 ffmpeg 
```

## 2.安装本项目依赖

你先要下载本项目源码，源码可以通过`git clone`命令下载，如果你不熟悉`git clone`命令。

你可以用浏览器打开这个地址`https://github.com/xinnan-tech/xiaozhi-esp32-server.git`

打开完，找到页面中一个绿色的按钮，写着`Code`的按钮，点开它，然后你就看到`Download ZIP`的按钮。

点击它，下载本项目源码压缩包。下载到你电脑后，解压它，此时它的名字可能叫`xiaozhi-esp32-server-main`
你需要把它重命名成`xiaozhi-esp32-server`，好了请记住这个目录，我们暂且称它为`项目目录`。

```
# 使用dos或者终端，进入到你的项目目录，执行以下命令
conda activate xiaozhi-esp32-server
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install -r requirements.txt
```

## 3.[跳转到下载语音识别模型文件](#模型文件)

## 4.[跳转到配置项目文件](#配置项目)

## 5.运行项目

```
# 确保在本项目的根目录下执行
conda activate xiaozhi-esp32-server
python app.py
```

## 6.[跳转到运行状态确认](#运行状态确认)

# 汇总

## 配置项目

修改`config.yaml`文件，配置本项目所需的各种参数。默认的LLM使用的是`ChatGLMLLM`
，你需要配置密钥，因为他们的模型，虽然有免费的，但是仍要去[官网](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)注册密钥，才能启动。
默认的TTS使用的是`EdgeTTS`，这个无需配置，如果你需要更换成`豆包TTS`，则需要配置密钥。

```
# 如果您是一名开发者，建议阅读以下内容。如果不是开发者，可以忽略这部分内容。
# 在开发中，在项目根目录创建data目录，将【config.yaml】复制一份，改成【.config.yaml】，放进data目录中
# 系统会优先读取【data/.config.yaml】文件的配置。
# 这样做，可以避免在提交代码的时候，错误地提交密钥信息，保护您的密钥安全。
```

配置说明：这里是各个功能使用的默认组件，例如LLM默认使用`ChatGLMLLM`模型。如果需要切换模型，就是改对应的名称。

本项目的默认配置仅是成本最低配置（`glm-4-flash`和`EdgeTTS`都是免费的），如果需要更优的更快的搭配，需要自己结合部署环境切换各组件的使用。

```
selected_module:
  ASR: FunASR
  VAD: SileroVAD
  LLM: ChatGLMLLM
  TTS: EdgeTTS
```

比如修改`LLM`使用的组件，就看本项目支持哪些`LLM` API接口，当前支持的是`openai`、`dify`。欢迎验证和支持更多LLM平台的接口。
使用时，在`selected_module`修改成对应的如下LLM配置的名称：

```
LLM:
  DeepSeekLLM:
    type: openai
    ...
  ChatGLMLLM:
    type: openai
    ...
  DifyLLM:
    type: dify
    ...
```

有些服务，比如如果你使用`Dify`、`豆包的TTS`，是需要密钥的，记得在配置文件加上哦！

## 模型文件

下载源码后，需要下载模型文件。 默认使用`SenseVoiceSmall`模型，进行语音转文字。因为模型较大，需要独立下载，下载后把`model.pt`
文件放在`model/SenseVoiceSmall`
目录下。下面两个下载路线任选一个。

- 线路一：阿里魔塔下载[SenseVoiceSmall](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt)
- 线路二：百度网盘下载[SenseVoiceSmall](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) 提取码:
  `qvna`


## 运行状态确认

如果首次执行，可能需要几分钟时间，你要耐心等待他完成拉取。正常拉取完成后，你可以在命令行执行以下命令查看服务是否启动成功

```
docker ps
```

如果你能看到`xiaozhi-server`，说明服务启动成功。那你还可以进一步执行以下命令，查看服务的日志

```
docker logs -f xiaozhi-esp32-server
```

如果你能看到，类似以下日志,则是本项目服务启动成功的标志。

```
2025-xx-xx xx:51:59,492 - core.server - INFO - Server is running at ws://xx.xx.xx.xxx:8000
2025-xx-xx xx:51:59,516 - websockets.server - INFO - server listening on 0.0.0.0:8000
```

接下来，你就可以开始 `编译esp32固件`了，请往下翻，翻到编译`esp32固件`相关章节。那么由于你是用docker部署，你要自己查看自己本机电脑的ip是多少。
正常来说，假设你的ip是`192.168.1.25`，那么你的接口地址就是：`ws://192.168.1.25:8000`。这个信息很有用的，后面`编译esp32固件`
需要用到。

请注意，你的接口地址是`websocket`协议的地址，你可以使用`apifox`等工具调试。但是不能直接用浏览器打开访问，如果用浏览器打开，日志会显示错误，会让你怀疑是否部署成功了。

## 版本升级操作

如果想升级版本，可以这么操作

1、备份好`config.yaml`文件，一些关键的配置到时复制到新的`config.yaml`文件里。

2、执行以下命令

```
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server
docker rmi ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

3、重新开始安装