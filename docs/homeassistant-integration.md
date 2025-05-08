# ESP32设备与HomeAssistant集成指南

## 简介

本文档将指导您如何将ESP32设备与HomeAssistant进行集成。

## 前提条件

- 已安装并配置好`HomeAssistant`
- 已经在HomeAssistant中集成`Xiaomi Home`，并将米家的设备导入进`HomeAssistant`
- `xiaozhi-esp32-server智控台`能正常使用
- 本次我选择的模型是：免费的ChatGLM，它支持functioncall函数调用

## 网络环境

1、我的`HomeAssistant`部署在下面，版本是`2025.3.4`
```
http://192.168.4.7:8123
```

2、我的`xiaozhi-esp32-server智控台`和`HomeAssistant`部署在同一台机器的另一个端口，版本是`0.3.10`
```
http://192.168.4.7:8002
```


## 配置步骤

### 1. 登录`HomeAssistant`整理需要控制的设备清单

登录`HomeAssistant`，点击`左下角的设置`，然后进入`设备与服务`，再点击顶部的`实体`。

然后在实体中搜索你相关控制的开关，结果出来后，在列表中，点击其中一个结果，这是会出现一个开关的界面。

在开关的界面，我们尝试点击开关，看看是开发会随着我们的点击开/关。如果能操作，说明是正常联网的。

接着在开关面板找到设置按钮，点击后，可以查看这个开关的`实体标识符`。

我们打开一个记事本，按照这样格式整理一条数据：

位置+英文逗号+设备名称+英文逗号+`实体标识符`+英文分号

例如，我在公司，我有一个玩具灯，他的标识符是switch.cuco_cn_460494544_cp1_on_p_2_1，那么就这个写这一条数据

```
公司,玩具灯,switch.cuco_cn_460494544_cp1_on_p_2_1;
```

当然最后我可能要操作两个灯，我的最终的结果是：

```
公司,玩具灯,switch.cuco_cn_460494544_cp1_on_p_2_1;
公司,台灯,switch.iot_cn_831898993_socn1_on_p_2_1;
```

这段字符，我们成为“设备清单字符”需要保存好，等一下有用。


### 2. 登录`HomeAssistant`拿到开发密钥

登录`HomeAssistant`，点击`左下角个人`，切换`安全`导航栏，划到底部`长期访问令牌`生成api_key。


### 3. 登录`智控台`

使用管理员账号，登录`智控台`。点击顶部菜单`参数管理`，搜索`plugins.home_assistant.`，会有三条结果出来

编辑`plugins.home_assistant.devices`，把刚才整理的设备清单字符粘贴进去。


编辑`plugins.home_assistant.base_url`，把你部署的`HomeAssistant`接口地址粘贴进去，我粘贴进去的地址是这样的

```
http://192.168.4.7:8123
```

编辑`plugins.home_assistant.api_key`，把你从`HomeAssistant`复制过来的密钥，粘贴进去


### 4. 设置`意图识别`函数

在智控台，点击顶部菜单“模型配置”，在左侧栏，找到“意图识别”，找到id为`Intent_function_call`的意图，点击编辑

然后在弹框中，在原来的基础上追加两个函数：“hass_get_state”和“hass_set_state”

修改前
```
change_role;get_weather;get_news;play_music
```

修改后

```
change_role;get_weather;get_news;play_music;hass_get_state;hass_set_state
```

### 6. 手动重启xiaozhi-server

重启xiaozhi-server程序


### 5. 确认角色配置是否设置了函数意图识别

在智控台，点击顶部菜单“智能体管理”，找到设备所在的智能体，点击“配置角色”

确认意图识别(Intent)，是否选择“函数调用意图识别”


### 6. 唤醒设别进行控制

尝试和esp32说，“打开XXX灯”