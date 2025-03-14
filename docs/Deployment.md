# 方式一：docker快速部署

docker镜像已支持x86架构、arm64架构的CPU，支持在国产操作系统上运行。

## 1. 安装docker

如果您的电脑还没安装docker，可以按照这里的教程安装：[docker安装](https://www.runoob.com/docker/ubuntu-docker-install.html)

> [!NOTE]
> 懒人脚本
>
> 你可以使用以下命令一键下载并执行部署脚本：
> ```bash
> curl -L -o docker-setup.sh https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/docker-setup.sh && chmod +x docker-setup.sh
> ```
>
> 如果您的电脑是windows系统，请使用powershell运行以下命令：
> ```bash
> bash docker-setup.sh
> ```
> 如果您的电脑是linux系统，请使用bash运行以下命令：
> ```bash
> ./docker-setup.sh
> ```
>
> 脚本会自动完成以下操作：
> 1. 创建必要的目录结构
> 2. 下载语音识别模型
> 3. 下载配置文件
> 4. 检查文件完整性
>
> 执行完成后，请按照提示配置 API 密钥。

## 2. 创建目录

安装完后，你需要为这个项目找一个安放配置文件的目录，例如我们可以新建一个文件夹叫`xiaozhi-server`。

创建好目录后，你需要在`xiaozhi-server`下面创建`data`文件夹和`models`文件夹，`models`下面还要再创建`SenseVoiceSmall`文件夹。


```bash
# 使用命令创建目录
mkdir -p xiaozhi-server/data xiaozhi-server/models/SenseVoiceSmall

# 进入到跟目录中
cd xiaozhi-server
```

## 3. 下载语音识别模型文件

你需要下载语音识别的模型文件，因为本项目的默认语音识别用的是本地离线语音识别方案。

可以通过以下两个线路之一下载：
- 线路一：[阿里魔塔下载 SenseVoiceSmall](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt)
- 线路二：[百度网盘下载 SenseVoiceSmall](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) (提取码: `qvna`)

```bash
# 如果使用线路一，可以直接用以下命令下载
curl -L --progress-bar -o models/SenseVoiceSmall/model.pt https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt
```

## 4. 下载配置文件

你需要下载两个配置文件：`docker-compose.yaml` 和 `config.yaml`。你可以通过以下命令下载，或者手动从项目仓库下载这两个文件。

### 4.1 下载 docker-compose.yaml

如果你的电脑安装了 curl 工具，可以直接使用以下命令下载：

```bash
curl -L --progress-bar -o docker-compose.yml https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/docker-compose.yml
```

如果没有安装 curl，你也可以直接用浏览器打开这个地址下载文件：
https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/docker-compose.yml

### 4.2 下载 config.yaml

> [!NOTE]
> 注意，`config.yaml` 文件需要放在 data 目录下，并且重命名成 `.config.yaml`

同样，可以使用 curl 命令下载：

```bash
curl -L --progress-bar -o data/.config.yaml https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/config.yaml
```

或者直接用浏览器打开这个地址下载：
https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/config.yaml

下载完成后，确认目录结构如下：

```bash
tree -L 3 -a
```

```plaintext
xiaozhi-server
  ├─ docker-compose.yml
  ├─ data
    ├─ .config.yaml
  ├─ models
     ├─ SenseVoiceSmall
       ├─ model.pt
```

## 5. 配置项目文件

请参考本文档末尾的[配置项目](#配置项目)部分进行配置。

## 6. 执行docker命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker logs -f xiaozhi-esp32-server
```

请参考本文档末尾的[运行状态确认](#运行状态确认)部分确认服务是否正常运行。

## 7. 版本升级操作

如果后期想升级版本，可以这么操作

1、备份好`data`文件夹中的`.config.yaml`文件，一些关键的配置到时复制到新的`.config.yaml`文件里。
请注意是对关键密钥逐个复制，不要直接覆盖。因为新的`.config.yaml`文件可能有一些新的配置项，旧的`.config.yaml`文件不一定有。

2、执行以下命令

```
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server
docker rmi ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest
```

3、重新按docker方式部署

# 方式二：借助Docker环境运行部署

开发人员如果不想安装`conda`环境，可以使用这种方法管理好依赖。

## 1.克隆项目

## 2.[跳转到下载语音识别模型文件](#模型文件)

## 3.[跳转到配置项目文件](#配置项目)

## 4.运行docker

修改完配置后，打开命令行工具，`cd`进入到你的`main/xiaozhi-server`下，执行以下命令

```sh
docker run -it --name xiaozhi-env --restart always --security-opt seccomp:unconfined \
  -p 8000:8000 \
  -p 8002:8002 \
  -v ./:/app \
  kalicyh/python:xiaozhi
```

然后就和正常开发一样了

## 5.安装依赖

在刚刚的打开的终端运行

```sh
pip install -r requirements.txt
```

## 6.运行项目

```sh
python app.py
```

# 方式三：本地源码运行

## 1.安装基础环境

本项目使用`conda`管理依赖环境。如果不方便安装`conda`，需要根据实际的操作系统安装好`libopus`和`ffmpeg`。
如果确定使用`conda`，则安装好后，开始执行以下命令。

重要提示！windows 用户，可以通过安装`Anaconda`来管理环境。安装好`Anaconda`后，在`开始`那里搜索`anaconda`相关的关键词，
找到`Anaconda Prpmpt`，使用管理员身份运行它。如下图。

![conda_prompt](./images/conda_env_1.png)

运行之后，如果你能看到命令行窗口前面有一个(base)字样，说明你成功进入了`conda`环境。那么你就可以执行以下命令了。

![conda_env](./images/conda_env_2.png)

```
conda remove -n xiaozhi-esp32-server --all -y
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server

# 添加清华源通道
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge

conda install libopus -y
conda install ffmpeg -y
```

请注意，以上命令，不是一股脑执行就成功的，你需要一步步执行，每一步执行完后，都检查一下输出的日志，查看是否成功。

## 2.安装本项目依赖

你先要下载本项目源码，源码可以通过`git clone`命令下载，如果你不熟悉`git clone`命令。

你可以用浏览器打开这个地址`https://github.com/xinnan-tech/xiaozhi-esp32-server.git`

打开完，找到页面中一个绿色的按钮，写着`Code`的按钮，点开它，然后你就看到`Download ZIP`的按钮。

点击它，下载本项目源码压缩包。下载到你电脑后，解压它，此时它的名字可能叫`xiaozhi-esp32-server-main`
你需要把它重命名成`xiaozhi-esp32-server`，在这个文件里，进入到`main`文件夹，再进入到`xiaozhi-server`，好了请记住这个目录`xiaozhi-server`。

```
# 继续使用conda环境
conda activate xiaozhi-esp32-server
# 进入到你的项目根目录，再进入main/xiaozhi-server
cd main/xiaozhi-server
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install -r requirements.txt
```

## 3.下载语音识别模型文件

你需要下载语音识别的模型文件，因为本项目的默认语音识别用的是本地离线语音识别方案。可通过这个方式下载
[跳转到下载语音识别模型文件](#模型文件)

下载完后，回到本教程。

## 4.配置项目文件

接下里，程序还不能直接运行，你需要配置一下，你到底使用的是什么模型。你可以看这个教程：
[跳转到配置项目文件](#配置项目)

## 5.运行项目

```
# 确保在xiaozhi-server目录下执行
conda activate xiaozhi-esp32-server
python app.py
```
这时，你就要留意日志信息，可以根据这个教程，判断是否成功了。[跳转到运行状态确认](#运行状态确认)


# 汇总

## 配置项目

如果你的`xiaozhi-server`目录没有`data`，你需要创建`data`目录。
如果你的`data`下面没有`.config.yaml`文件，你可以把源码目录下的`config.yaml`文件复制一份，重命名为`.config.yaml`

修改`xiaozhi-server`下`data`目录下的`.config.yaml`文件，配置本项目必须的两个配置。

- 默认的LLM使用的是`ChatGLMLLM`，你需要配置密钥，因为他们的模型，虽然有免费的，但是仍要去[官网](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)注册密钥，才能启动。
- 默认的记忆层`mem0ai`，你需要配置密钥，因为他们的API，虽然有免费额度，但是仍要去[官网](https://app.mem0.ai/dashboard/api-keys)注册密钥，才能启动。

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

本项目语音识别模型，默认使用`SenseVoiceSmall`模型，进行语音转文字。因为模型较大，需要独立下载，下载后把`model.pt`
文件放在`models/SenseVoiceSmall`
目录下。下面两个下载路线任选一个。

- 线路一：阿里魔塔下载[SenseVoiceSmall](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt)
- 线路二：百度网盘下载[SenseVoiceSmall](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) 提取码:
  `qvna`

## 运行状态确认

如果你能看到，类似以下日志,则是本项目服务启动成功的标志。

```
25-02-23 12:01:09[core.websocket_server] - INFO - Server is running at ws://xxx.xx.xx.xx:8000
25-02-23 12:01:09[core.websocket_server] - INFO - =======上面的地址是websocket协议地址，请勿用浏览器访问=======
```

正常来说，如果您是通过源码运行本项目，日志会有你的接口地址信息。
但是如果你用 `docker` 部署，那么你的日志里给出的接口地址信息就不是真实的接口地址。

最正确的方法，是根据电脑的局域网IP来确定你的接口地址。
如果你的电脑的局域网IP比如是`192.168.1.25`，那么你的接口地址就是：`ws://192.168.1.25:8000`。

这个地址涉及到固件是否能够链接上服务端，请务必记住，后面`编译esp32固件`需要用到。

接下来，你就可以开始 [编译esp32固件](firmware-build.md)了。


## 常见问题

1. [为什么我说的话，小智识别出来很多韩文、日文、英文？](../README.md#asr-recognition-issue)

2. [为什么会出现"TTS 任务出错 文件不存在"？](../README.md#tts-file-error)

3. [TTS 经常失败，经常超时](../README.md#tts-timeout-issue)

4. [如何提高小智对话响应速度？](../README.md#performance-optimization)

5. [我说话很慢，停顿时小智老是抢话](../README.md#speech-interruption)

6. [我想通过小智控制电灯、空调、远程开关机等操作](../README.md#home-automation)
