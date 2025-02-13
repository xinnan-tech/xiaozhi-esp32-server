![图片](docs/images/banner.png)

# 小智 ESP-32 后端服务(xiaozhi-esp32-server)

（中文 | [English](README_en.md)）

本项目为开源智能硬件项目 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)
提供后端服务。根据[小智通信协议](https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh)使用`Python`实现。

## 适用人群

本项目需要配合esp32硬件设备使用，如果童鞋们已经购买了esp32相关硬件，且成功对接虾哥部署的后端，并且想自己独立搭建
`xiaozhi-esp32`后端服务，可学习本项目。

想看使用效果,请猛戳这个视频

<a href="https://www.bilibili.com/video/BV1FMFyejExX">
 <picture>
   <img alt="小智esp32连接自己的后台模型" src="docs/images/demo.png" />
 </picture>
</a>

要想完整体验本项目，需要以下总体步骤：

- 准备一套兼容`xiaozhi-esp32`
  项目的硬件设备，具体型号可[点击这里](https://rcnv1t9vps13.feishu.cn/wiki/DdgIw4BUgivWDPkhMj1cGIYCnRf)。
- 拥有一台至少4核CPU 8G内存的普通电脑或服务器，运行本项目。部署后可以在控制台看到本项目服务的接口地址。
- 下载`xiaozhi-esp32`项目，把`接口地址`修改成本项目地址，然后编译，把新固件烧录到硬件设备上。
- 启动设备，查看电脑或服务器的控制台，如果看到日志，说明成功连到本项目的接口了。

## 警告

本项目成立时间较短，还未通过网络安全测评，请勿在生产环境中使用。

## 功能清单

## 已实现

- `xiaozhi-esp32` 通信 WebSocket 协议
- 支持唤醒对话、手动对话、实时打断对话
- 支持国语、粤语、英语、日语、韩语 5 种语言识别（FunASR（默认））
- 自由更换 LLM（支持ChatGLM（默认）、阿里百炼、Dify、DeepSeek）
- 自由更换 TTS（支持EdgeTTS（默认）、火山引擎豆包TTS）

## 正在实现

- 长时间不聊天进入休眠状态
- 对话记忆
- 更换心情模式

## 本项目支持的平台/组件列表

| 类型  | 平台名称      | 使用方式 | 收费模式    | 备注                                                              |
|:----|:----------|:----:|:--------|:----------------------------------------------------------------|
| LLM | 阿里百炼      | 接口调用 | 消耗token | [点击申请密钥](https://bailian.console.aliyun.com/?apiKey=1#/api-key) |
| LLM | 深度求索      | 接口调用 | 消耗token | [点击申请密钥](https://platform.deepseek.com/)                        |
| LLM | Dify      | 接口调用 | 消耗token | 本地化部署                                                           |
| LLM | 智谱        | 接口调用 | 免费      | [点击创建密钥](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)      |
| TTS | 火山引擎      | 接口调用 | 消耗token | [点击创建密钥](https://console.volcengine.com/speech/service/8)       |
| TTS | EdgeTTS   | 接口调用 | 免费      |                                                                 |
| VAD | SileroVAD | 本地使用 | 免费      |                                                                 |
| ASR | FunASR    | 本地使用 | 免费      |                                                                 |

# 部署方式

本项目支持docker快速部署和本地源码运行。如果您主要是想快速体验，推荐使用docker部署。如果想深入了解本项目，推荐本地源码运行。

## 方式一：docker快速部署

docker镜像已支持x86架构、arm64架构的CPU，支持在国产操作系统上运行。

### 1. 安装docker

如果您的电脑还没安装docker，可以按照这里的教程安装：[docker安装](https://www.runoob.com/docker/ubuntu-docker-install.html)

### 2. 创建目录

安装完后，你需要为这个项目找一个安放配置文件的目录，我们暂且称它为`项目目录`，这个目录最好是一个新建的空的目录。

### 3. 下载配置文件

用浏览器打开[这个链接](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/config.yaml)。

在页面的右侧找到名称为`RAW`按钮，在`RAW`按钮的旁边，找到下载的图标，点击下载按钮，下载`config.yaml`文件。 把文件下载到你的
`项目目录`。

### 4. 修改配置文件

修改刚才你下载的`config.yaml`文件，配置本项目所需的各种参数。默认的LLM使用的是`ChatGLMLLM`，你需要配置密钥，才能启动。

默认的TTS使用的是`EdgeTTS`，这个无需配置，如果你需要更换成`豆包TTS`，则需要配置密钥。

配置说明：这里是各个功能使用的默认组件，例如LLM默认使用`ChatGLMLLM`模型。如果需要切换模型，就是改对应的名称。

本项目的默认配置原则是成本最低配置原则（`glm-4-flash`和`EdgeTTS`都是免费的），如果需要更优的更快的搭配，需要自己结合部署环境切换各组件的使用。

```
selected_module:
  ASR: FunASR
  VAD: SileroVAD
  LLM: ChatGLMLLM
  TTS: EdgeTTS
```

比如修改`LLM`使用的组件，就看本项目支持哪些`LLM`，如下就是支持`DeepSeekLLM`、`ChatGLMLLM`。你们在`selected_module`修改成对应的LLM

```
LLM:
  AliLLM:
    ...
  DeepSeekLLM:
    ...
  ChatGLMLLM:
    ...
  DifyLLM:
    ...
```

有些服务，比如如果你使用`Dify`、`豆包的TTS`，是需要密钥的，记得在配置文件加上哦！

### 5. 执行docker命令

打开命令行工具，`cd` 进入到你的`项目目录`，执行以下命令

```
#如果你是linux，执行
ls
#如果你是windows，执行
dir
```

如果你能看到`config.yaml`文件，确确实实进入到了`项目目录`，接着执行以下命令：

```
docker run -d --name xiaozhi-esp32-server --restart always --security-opt seccomp:unconfined -p 8000:8000 -v $(pwd)/config.yaml:/opt/xiaozhi-es32-server/config.yaml ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

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

后期如果想升级版本，可以这么操作

1、备份好`config.yaml`文件，一些关键的配置到时复制到新的`config.yaml`文件里。

2、执行以下命令

```
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server
docker rmi ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
```

3.按本教程重新来一遍

## 方式二：本地源码运行

### 1.安装基础环境

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

### 2.安装本项目依赖

```
# 拉取本项目后进入本项目根目录
cd xiaozhi-esp32-server
conda activate xiaozhi-esp32-server
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install -r requirements.txt
```

### 3.下载语音识别模型

默认使用`SenseVoiceSmall`模型，进行语音转文字。因为模型较大，需要独立下载，下载后把`model.pt`文件放在`model/SenseVoiceSmall`
目录下。下面两个下载路线任选一个。

- 线路一：阿里魔塔下载[SenseVoiceSmall](https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt)
- 线路二：百度网盘下载[SenseVoiceSmall](https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg&pwd=qvna) 提取码:
  `qvna`

### 4.配置项目

修改`config.yaml`文件，配置本项目所需的各种参数。默认的LLM使用的是`ChatGLMLLM`，你需要配置密钥，才能启动。
默认的TTS使用的是`EdgeTTS`，这个无需配置，如果你需要更换成`豆包TTS`，则需要配置密钥。

配置说明：这里是各个功能使用的默认组件，例如LLM默认使用`ChatGLMLLM`模型。如果需要切换模型，就是改对应的名称。

本项目的默认配置仅是成本最低配置（`glm-4-flash`和`EdgeTTS`都是免费的），如果需要更优的更快的搭配，需要自己结合部署环境切换各组件的使用。

```
selected_module:
  ASR: FunASR
  VAD: SileroVAD
  LLM: ChatGLMLLM
  TTS: EdgeTTS
```

比如修改`LLM`使用的组件，就看本项目支持哪些`LLM`，如下就是支持`DeepSeekLLM`、`ChatGLMLLM`。你们在`selected_module`修改成对应的LLM

```
LLM:
  DeepSeekLLM:
    ...
  ChatGLMLLM:
    ...
  DifyLLM:
    ...
```

有些服务，比如如果你使用`Dify`、`豆包的TTS`，是需要密钥的，记得在配置文件加上哦！

### 5.运行项目

启动项目

```
# 确保在本项目的根目录下执行
conda activate xiaozhi-esp32-server
python app.py
```

启动后，会看到类似以下日志

```
2025-xx-xx xx:51:59,492 - core.server - INFO - Server is running at ws://192.168.1.25:8000
2025-xx-xx xx:51:59,516 - websockets.server - INFO - server listening on 0.0.0.0:8000
```

其中上面的`ws://192.168.1.25:8000`就是本项目提供的接口地址了，当然你自己的机器和我的是不一样的，记得要找到自己的地址。

# 编译esp32固件

1. 下载`xiaozhi-esp32`
   项目，按照这个教程配置项目环境[《Windows搭建 ESP IDF 5.3.2开发环境以及编译小智》](https://icnynnzcwou8.feishu.cn/wiki/JEYDwTTALi5s2zkGlFGcDiRknXf)

2. 打开`xiaozhi-esp32/main/Kconfig.projbuild`文件，找到`WEBSOCKET_URL`的`default`的内容，把`wss://api.tenclass.net`
   改成你自己的地址，例如，我的接口地址是`ws://192.168.1.25:8000`，就把内容改成这个。

修改前：

```
config WEBSOCKET_URL
    depends on CONNECTION_TYPE_WEBSOCKET
    string "Websocket URL"
    default "wss://api.tenclass.net/xiaozhi/v1/"
    help
        Communication with the server through websocket after wake up.
```

修改后(示例)：

```
config WEBSOCKET_URL
    depends on CONNECTION_TYPE_WEBSOCKET
    string "Websocket URL"
    default "ws://192.168.1.25:8000/xiaozhi/v1/"
    help
        Communication with the server through websocket after wake up.
```

3. 设置编译参数

```
# 终端命令行进入xiaozhi-esp32的根目录
cd xiaozhi-esp32
# 例如我使用的板子是esp32s3，所以设置编译目标为esp32s3，如果你的板子是其他型号，请替换成对应的型号
idf.py set-target esp32s3
# 进入菜单配置
idf.py menuconfig
```

![图片](docs/images/build_setting01.png)

进入菜单配置后，再进入`Xiaozhi Assistant`，将`CONNECTION_TYPE`设置为`Websocket`
回退到主菜单，再进入`Xiaozhi Assistant`，将`BOARD_TYPE`设置你板子的具体型号
保存退出，回到终端命令行。

![图片](docs/images/build_setting02.png)

4. 编译固件

```
idf.py build
```

5. 打包bin固件

```
cd scripts
python release.py
```

编译成功后，会在项目根目录下的`build`目录下生成固件文件`merged-binary.bin`。
这个`merged-binary.bin`就是要烧录到硬件上的固件文件。

6. 烧录固件
   将esp32设备连接电脑，使用chrome浏览器，打开以下网址

```
https://espressif.github.io/esp-launchpad/
```

打开这个教程，[Flash工具/Web端烧录固件（无IDF开发环境）](https://ccnphfhqs21z.feishu.cn/wiki/Zpz4wXBtdimBrLk25WdcXzxcnNS)。
翻到：`方式二：ESP-Launchpad 浏览器WEB端烧录`，从`3. 烧录固件/下载到开发板`开始，按照教程操作。

# 常见问题

## 1、TTS 经常失败，经常超时

建议：如果`EdgeTTS`经常失败，先检查一下是否用了梯子，如果用了梯子，请把梯子关了试试。
如果用的是`火山引擎的豆包TTS`经常失败，最好使用付费版本，因为他们的测试版本只有2个并发。

## 2、我想通过小智控制电灯、空调、远程开关机等操作。

建议：在配置文件里，将`LLM`设置成`DifyLLM`，然后通过`Dify`编排智能体实现。

## 3、我说话很慢，我停顿一下，小智老是抢我的话，咋办。

建议：在配置文件里，找到这一段，将`min_silence_duration_ms`值改大一点，比如改成`1000`。

```
VAD:
  SileroVAD:
    threshold: 0.5
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 700  # 如果说话停顿比较长，可以把这个值设置大一些
```

## 4、如何才能提高小智对话响应速度？

本项目的默认配置，是成本最低的配置。建议刚上手的童鞋，使用默认的免费模型，先解决了“跑得动”的问题，再解决“跑得快”的问题。
如果要提高响应速度，需要更换各组件来解决。以下是本项目各组件的响应速度测试Tip。

以下内容和结论仅供参考，不构成任何形式的承诺或保证。

### LLM 类组件

| 排名 | 组件名称        | 响应速度(ms) |
|:---|:------------|:--------:|
| 1  | AliLLM      |   630    |
| 2  | ChatGLMLLM  |   2000   | 
| 3  | DeepSeekLLM |   6800   | 

```
测试地点：广东省佛山市禅城区
测试时间：2025年2月9日 16:12
宽带运营商：中国移动
测试方法：更换配置后，执行core/utils/llm.py文件
```

### TTS 类组件

| 排名 | 组件名称      | 响应速度(ms) |
|:---|:----------|:--------:|
| 1  | DoubaoTTS |   645    |
| 2  | EdgeTTS   |   1019   |

```
测试地点：广东省佛山市禅城区
测试时间：2025年2月9日 16:12
宽带运营商：中国移动
测试方法：更换配置后，执行core/utils/tts.py文件

```

### 结论

`2025年2月9日`，如果我的电脑在`广东省佛山市禅城区`，且使用的是`中国移动`网络，我会优先使用：

- LLM：`AliLLM`
- TTS：`DoubaoTTS`

## 5、更多问题，可联系我们反馈

![图片](docs/images/wechat.jpg)

# 鸣谢

- 本项目受[百聆语音对话机器人](https://github.com/wwbin2017/bailing)项目启发，基于该项目的基础思路完成实现。
- 感谢[腾讯云](https://cloud.tencent.com/)为本次项目提供免费docker镜像空间。
- 感谢[十方融海](https://www.tenclass.com/)在小智通讯协议上提供充分的文档支持。

<a href="https://star-history.com/#xinnan-tech/xiaozhi-esp32-server&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>