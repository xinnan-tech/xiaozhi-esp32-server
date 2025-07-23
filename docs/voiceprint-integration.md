# 声纹识别启用指南

本教程包含3个部分
- 1、如何部署声纹识别这个服务
- 2、全模块部署时，怎么配置声纹识别接口
- 3、最简化部署时，怎么配置声纹识别

# 1、如何部署声纹识别这个服务

## 第一步，下载声纹识别项目源码

浏览器打开[声纹识别项目地址](https://github.com/xinnan-tech/voiceprint-api)

打开完，找到页面中一个绿色的按钮，写着`Code`的按钮，点开它，然后你就看到`Download ZIP`的按钮。

点击它，下载本项目源码压缩包。下载到你电脑后，解压它，此时它的名字可能叫`voiceprint-api-main`
你需要把它重命名成`voiceprint-api`。

## 第二步， 创建数据库和表

声纹识别需要依赖`mysql`数据库。如果你之前已经部署`智控台`，说明你已经安装了`mysql`。你可以共用它。

你可以你试一下在宿主机使用`telnet`命令，看看能不能正常访问`mysql`的`3306`端口。
```
telnet 127.0.0.1 3306
```
如果能访问到3306端口，请忽略以下的内容，直接进入第三步。

如果不能访问，你需要回忆一下，你的`mysql`是怎么安装的。

如果你的mysql是通过自己使用安装包安装的，说明你的`mysql`做了网络隔离。你可能先解访问`mysql`的`3306`端口这个问题。

如果你`mysql`是通过本项目的`docker-compose_all.yml`安装的。你需要找一下你当时创建数据库的`docker-compose_all.yml`文件，修改以下的内容

修改前
```
  xiaozhi-esp32-server-db:
    ...
    networks:
      - default
    expose:
      - "3306:3306"
```

修改后
```
  xiaozhi-esp32-server-db:
    ...
    networks:
      - default
    ports:
      - "3306:3306"
```

注意是将`xiaozhi-esp32-server-db`下面的`expose`改成`ports`。改完后，需要重新启动。以下是重启mysql的命令：

```
# 进入你docker-compose_all.yml所在的文件夹，例如我的是xiaozhi-server
cd xiaozhi-server
docker compose -f docker-compose_all.yml down
docker compose -f docker-compose.yml up -d
```

启动完后，在宿主机再使用`telnet`命令，看看能不能正常访问`mysql`的`3306`端口。
```
telnet 127.0.0.1 3306
```
正常来说这样就可以访问的了。

## 第三步， 创建数据库和表
如果你的宿主机，能正常访问mysql数据库，那就在mysql上创建一个名字为`voiceprint_db`的数据库和`voiceprints`表。

```
CREATE DATABASE voiceprint_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE voiceprint_db;

CREATE TABLE voiceprints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    speaker_id VARCHAR(255) NOT NULL UNIQUE,
    feature_vector LONGBLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_speaker_id (speaker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 第四步， 配置数据库连接

进入`voiceprint-api`文件夹，创建名字为`data`的文件夹。

把`voiceprint-api`根目录里的`voiceprint.yaml`，复制到`data`的文件夹，将它重命名为`.voiceprint.yaml`

接下来，你需要重点配置一下`.voiceprint.yaml`里的数据库连接。

```
mysql:
  host: "127.0.0.1"
  port: 3306
  user: "root"
  password: "your_password"
  database: "voiceprint_db"
```

注意！由于你的声纹识别服务是使用docker部署，`host`需要填写成你`mysql所在机器的局域网ip`。

注意！由于你的声纹识别服务是使用docker部署，`host`需要填写成你`mysql所在机器的局域网ip`。

注意！由于你的声纹识别服务是使用docker部署，`host`需要填写成你`mysql所在机器的局域网ip`。

## 第五步，启动程序
这个项目是一个很简单的项目，建议使用docker运行。不过如果你不想使用docker运行，你可以参考[这个页面](https://github.com/xinnan-tech/voiceprint-api/blob/main/README.md)使用源码运行。以下是docker运行的方法

```
# 进入本项目源码根目录
cd voiceprint-api

# 清除缓存
docker compose -f docker-compose.yml down
docker stop voiceprint-api
docker rm voiceprint-api
docker rmi ghcr.nju.edu.cn/xinnan-tech/voiceprint-api:latest

# 启动docker容器
docker compose -f docker-compose.yml up -d
# 查看日志
docker logs -f voiceprint-api
```

此时，日志里会输出类似以下的日志
```
250711 INFO-🚀 开始: 生产环境服务启动（Uvicorn），监听地址: 0.0.0.0:8005
250711 INFO-============================================================
250711 INFO-声纹接口地址: http://127.0.0.1:8005/voiceprint/health?key=abcd
250711 INFO-============================================================
```

请你把声纹接口地址复制出来：

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

你先把地址复制出来，放在一个草稿里，你要知道你的电脑的局域网ip是什么，例如我的电脑局域网ip是`192.168.1.25`，那么
原来我的接口地址
```
http://127.0.0.1:8005/voiceprint/health?key=abcd

```
就要改成
```
http://192.168.1.25:8005/voiceprint/health?key=abcd
```

改好后，请使用浏览器直接访问`声纹接口地址`。当浏览器出现类似这样的代码，说明是成功了。
```
{"total_voiceprints":0,"status":"healthy"}
```

请你保留好修改后的`声纹接口地址`，下一步要用到。

# 2、全模块部署时，怎么配置声纹识别

## 第一步 配置接口
如果你是全模块部署，使用管理员账号，登录智控台，点击顶部`参数字典`，选择`参数管理`功能。

然后搜索参数`server.voice_print`，此时，它的值应该是`null`值。
点击修改按钮，把上一步得来的`声纹接口地址`粘贴到`参数值`里。然后保存。

如果能保存成功，说明一切顺利，你可以去智能体查看效果了。如果不成功，说明智控台无法访问声纹识别，很大概率是网络防火墙，或者没有填写正确的局域网ip。

## 第二步 设置智能体记忆模式

进入你的智能体的角色配置里，将记忆设置成`本地短期记忆`，一定要开启`上报文字+语音`。

## 第三步 和你的智能体聊天

将你的设备通电，然后和他用正常的语速和音调聊天。

## 第四步 设置声纹

在智控台，`智能体管理`页面，在智能体的面板里，有一个`声纹识别`按钮，点击它。在底部有一个`新增按钮`。就可以对某个人说的话进行声纹注册。
在弹出的框里，`描述`这个属性建议填写上，可以是这个人的职业、性格、爱好。方便智能体对说话人进行分析和了解。

## 第三步 和你的智能体聊天

将你的设备通电，问它，你知道我是谁吗？如果他能回答得出，说明声纹识别功能正常。

# 3、最简化部署时，怎么配置声纹识别

## 第一步 配置接口
打开 `xiaozhi-server/data/.config.yaml` 文件（如果没有需要创建），然后添加/修改以下内容：

```
# 声纹识别配置
voiceprint:
  # 声纹接口地址
  url: 你的声纹接口地址
  # 说话人配置：speaker_id,名称,描述
  speakers:
    - "test1,张三,张三是一个程序员"
    - "test2,李四,李四是一个产品经理"
    - "test3,王五,王五是一个设计师"
```

把上一步得来的 `声纹接口地址` 粘贴到 `url` 里。然后保存。

`speakers` 参数依据需求添加。这里需要注意这个 `speaker_id` 参数，后面注册声纹会用到。

## 第二步 注册声纹
如果你已经启动了声纹服务，本地浏览器里访问 `http://localhost:8005/voiceprint/docs` 即可查看 API 文档，这里只说明注册声纹的 API 如何使用。

注册声纹的 API 地址为 `http://localhost:8005/voiceprint/register`，请求方式为 POST。

请求头需要包含 Bearer Token 认证，token 为 `声纹接口地址` 中 `?key=` 后的部分，比如如果我的声纹注册地址为 `http://127.0.0.1:8005/voiceprint/health?key=abcd`，那么我的 token 就是`abcd`。

请求体包含说话人 ID（speaker_id），和 WAV 音频文件（file），请求示例如下：

```
curl -X POST \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "speaker_id=your_speaker_id_here" \
  -F "file=@/path/to/your/file" \
  http://localhost:8005/voiceprint/register
```

 这里的 `file` 是要注册的说话人说话的音频文件， `speaker_id` 需要和第一步配置接口的 `speaker_id` 保持一致。比如说我需要注册张三的声纹，在 `.config.yaml` 中填的张三的 `speaker_id` 为 `test1`，那么我注册张三声纹的时候，请求体里填的 `speaker_id` 就是 `test1`， `file` 填的就是张三说一段话的音频文件。

 ## 第三步 启动服务

启动小智服务器和声纹服务，即可正常使用。
