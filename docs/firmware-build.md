# esp32固件编译

## 第1步 准备你的ota地址

如果你，使用的是本项目0.3.12版本，不管是简单Server部署还是全模块部署，都会有ota地址。

由于简单Server部署和全模块部署的OTA地址设置方式不一样，请你选择下面的具体方式：

### 如果你用的是简单Server部署
此刻，请你用浏览器打开你的ota地址，例如我的ota地址
```
http://192.168.1.25:8002/xiaozhi/ota/
```
如果显示“OTA接口运行正常，向设备发送的websocket地址是：ws://xxx:8000/xiaozhi/v1/

你可以使用项目自带的`test_page.html`测试一下，是否能连上ota页面输出的websocket地址。

如果访问不到，你需要到配置文件`.config.yaml`里修改`server.websocket`的地址，重启后再重新测试，直到`test_page.html`能正常访问。

成功后，请往下进行第2步

### 如果你用的是全模块部署
此刻，请你用浏览器打开你的ota地址，例如我的ota地址
```
http://192.168.1.25:8002/xiaozhi/ota/
```

如果显示“OTA接口运行正常，websocket集群数量：X”。那就往下进行2步。

如果显示“OTA接口运行不正常”，大概是你还没在`智控台`配置`Websocket`地址。那就：

- 1、使用超级管理员登录智控台

- 2、顶部菜单点击`参数管理`

- 3、在列表中找到`server.websocket`项目，输入你的`Websocket`地址。例如我的就是

```
ws://192.168.1.25:8000/xiaozhi/v1/
```

配置完后，再使用浏览器刷新你的ota接口地址，看看是不是正常了。如果还不正常就，就再次确认一下Websocket是否正常启动，是否配置了Websocket地址。

## 第2步 配置环境
先按照这个教程配置项目环境[《Windows搭建 ESP IDF 5.3.2开发环境以及编译小智》](https://icnynnzcwou8.feishu.cn/wiki/JEYDwTTALi5s2zkGlFGcDiRknXf)

## 第3步 打开配置文件
配置好编译环境后，下载虾哥iaozhi-esp32项目源码，

从这里下载虾哥[xiaozhi-esp32项目源码](https://github.com/78/xiaozhi-esp32)。

下载后，打开`xiaozhi-esp32/main/Kconfig.projbuild`文件。

## 第4步 修改OTA地址

找到`OTA_URL`的`default`的内容，把`https://api.tenclass.net/xiaozhi/ota/`
   改成你自己的地址，例如，我的接口地址是`http://192.168.1.25:8002/xiaozhi/ota/`，就把内容改成这个。

修改前：
```
config OTA_URL
    string "Default OTA URL"
    default "https://api.tenclass.net/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```
修改后：
```
config OTA_URL
    string "Default OTA URL"
    default "http://192.168.1.25:8002/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```

## 第4步 设置编译参数

设置编译参数

```
# 终端命令行进入xiaozhi-esp32的根目录
cd xiaozhi-esp32
# 例如我使用的板子是esp32s3，所以设置编译目标为esp32s3，如果你的板子是其他型号，请替换成对应的型号
idf.py set-target esp32s3
# 进入菜单配置
idf.py menuconfig
```

进入菜单配置后，再进入`Xiaozhi Assistant`，将`BOARD_TYPE`设置你板子的具体型号
保存退出，回到终端命令行。

## 第5步 编译固件

```
idf.py build
```

## 第6步 打包bin固件

```
cd scripts
python release.py
```

上面的打包命令执行完成后，会在项目根目录下的`build`目录下生成固件文件`merged-binary.bin`。
这个`merged-binary.bin`就是要烧录到硬件上的固件文件。

注意：如果执行到第二命令后，报了“zip”相关的错误，请忽略这个错误，只要`build`目录下生成固件文件`merged-binary.bin`
，对你没有太大影响，请继续。

## 第7步 烧录固件
   将esp32设备连接电脑，使用chrome浏览器，打开以下网址

```
https://espressif.github.io/esp-launchpad/
```

打开这个教程，[Flash工具/Web端烧录固件（无IDF开发环境）](https://ccnphfhqs21z.feishu.cn/wiki/Zpz4wXBtdimBrLk25WdcXzxcnNS)。
翻到：`方式二：ESP-Launchpad 浏览器WEB端烧录`，从`3. 烧录固件/下载到开发板`开始，按照教程操作。

烧录成功且联网成功后，通过唤醒词唤醒小智，留意server端输出的控制台信息。

## 常见问题
以下是一些常见问题，供参考：

[1、为什么我说的话，小智识别出来很多韩文、日文、英文](./FAQ.md)

[2、为什么会出现“TTS 任务出错 文件不存在”？](./FAQ.md)

[3、TTS 经常失败，经常超时](./FAQ.md)

[4、使用Wifi能连接自建服务器，但是4G模式却接不上](./FAQ.md)

[5、如何提高小智对话响应速度？](./FAQ.md)

[6、我说话很慢，停顿时小智老是抢话](./FAQ.md)

[7、我想通过小智控制电灯、空调、远程开关机等操作](./FAQ.md)
