# 设备间相互呼叫插件使用指南

## 概述

设备呼叫功能允许两个已配置设备之间通过语音/数据通道进行双向通信。设备A呼叫设备B时，系统通过以下流程实现：

```
设备A → 授权校验 → MQTT网关 → 设备B远程唤醒 → 建立连接 → 通话建立
```
## 使用这个功能的前提条件
1. 你必须要有至少两个设备，每个设备型号必须是`ESP32-S3`，因为只有`ESP32-S3`才支持远程唤醒功能。
2. 你的设备必须要有`两个麦克风`。但是如果你的设备只有`单个麦克风`，你只是想体验一下这个功能，也是可以的，但是会有强烈的卡顿感。
3. 你必须使用[全模块部署](Deployment_all.md)本项目，因为你需要`智控台`来管理设备的权限和通信。
4. 你必须安装并配置好`2026年5月27日`以后的[MQTT网关服务](mqtt-gateway-integration.md)，如果你已经部署了MQTT网关服务，请确认代码的版本是`2026年5月27日`之后的版本。

以上是使用这个功能的硬性条件，接下来会详细介绍。

## 配置步骤

### 第一步：开启通讯录功能

1. 确认你的智控台版本是`0.9.4`或以上版本。
2. 登录智控台后台
3. 进入 **系统功能配置**
4. 在左侧功能列表中勾选 **通讯录**
5. 点击 **保存配置** 确认

### 第二步：配置设备间呼叫权限

1. 在智控台顶部菜单点击 **通讯录**
2. 在左侧智能体下，设备列表中选择你的设备A（支持按 MAC地址 或 备注名 搜索）
3. 在右侧详情面板中，找到目标设备B的称呼设置，例如 **"小王"**
4. 勾选设备B的 **呼叫权限** 复选框
5. 点击 **保存**

**双向授权说明：** 如需设备A和设备B互相通信，必须在两侧智控台分别配置对方权限。例如：

- 在设备A的配置中勾选设备B → 设备A可与设备B通信
- 在设备B的配置中勾选设备A → 设备B可与设备A通信

### 第三步：在智能体配置添加呼叫工具

1. 在智控台顶部菜单点击 **智能体管理**
2. 在刚刚配置设备联系人的相关智能体中点击 **编辑角色**
3. 在右侧详情面板中，点击 **编辑功能**
4. 勾选 **设备呼叫设备** 工具
5. 点击 **保存配置** 确认
6. 在外侧再次点击 **保存配置** ，随即重启设备

### 第四步：固件端添加远程唤醒工具

1. 在[xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 代码的基础上增加远程唤醒工具MCP，版本支持为2.1.0至2.2.6（2026年5月29日的版本）
2. 在application.h文件中添加远程唤醒函数声明
    ```cpp
    void RemoteWakeup(const std::string& reason);
    ```
3. 在application.cc文件中添加远程唤醒函数
    ```cpp
    void Application::RemoteWakeup(const std::string& reason){
        if (!protocol_) {
            return;
        }

        auto state = GetDeviceState();
        
        if (state == kDeviceStateIdle) {
            audio_service_.EncodeWakeWord();

            if (!protocol_->IsAudioChannelOpened()) {
                SetDeviceState(kDeviceStateConnecting);
                if (!protocol_->OpenAudioChannel()) {
                    audio_service_.EnableWakeWordDetection(true);
                    return;
                }
            }
            std::string wake_word = reason;
    #if CONFIG_USE_AFE_WAKE_WORD || CONFIG_USE_CUSTOM_WAKE_WORD
            // Encode and send the wake word data to the server
            while (auto packet = audio_service_.PopWakeWordPacket()) {
                protocol_->SendAudio(std::move(packet));
            }
            // Set the chat state to wake word detected
            protocol_->SendWakeWordDetected(wake_word);
            SetListeningMode(aec_mode_ == kAecOff ? kListeningModeAutoStop : kListeningModeRealtime);
    #else
            // Set flag to play popup sound after state changes to listening
            // (PlaySound here would be cleared by ResetDecoder in EnableVoiceProcessing)
            play_popup_on_listening_ = true;
            SetListeningMode(aec_mode_ == kAecOff ? kListeningModeAutoStop : kListeningModeRealtime);
    #endif
        } else if (state == kDeviceStateSpeaking) {
            AbortSpeaking(kAbortReasonWakeWordDetected);
            SetDeviceState(kDeviceStateIdle);
        } else if (state == kDeviceStateActivating) {
            SetDeviceState(kDeviceStateIdle);
        }
    }
    ```
4. 在mcp_server.cc文件中添加远程唤醒工具
    ```cpp
    AddUserOnlyTool("self.remote_wakeup", "Remote wakeup function with configurable parameters",
        PropertyList({
            Property("reason", kPropertyTypeString, "Wakeup reason"),
        }),
        [this](const PropertyList& properties) -> ReturnValue {
            std::string reason = properties["reason"].value<std::string>();
            ESP_LOGI(TAG, "Wakeup reason=%s", reason.c_str());
            auto& app = Application::GetInstance();
            app.RemoteWakeup(reason);
            return true;
    ```
5. 按照 [固件编译烧录指南](firmware-build.md) 完成固件烧录
6. 无论你的设备是单麦还是双麦，请在编译环节，勾选开启AEC功能!
7. 无论你的设备是单麦还是双麦，请在编译环节，勾选开启AEC功能!
8. 无论你的设备是单麦还是双麦，请在编译环节，勾选开启AEC功能!

### 第五步：配置MQTT网关服务

1. 部署MQTT网关服务，参考 [MQTT网关集成文档](mqtt-gateway-integration.md)
2. 如果已经部署请确认代码的版本是2026年5月27日的版本

## 呼叫流程说明

准备两个设备，在智控台上面配置好通讯权限和在智能体中添加呼叫工具之后，在其中一个小智对话那里对他说：”呼叫XXX“，观察设备B是否响应。

## 常见问题

### Q: 设备B没有响应呼叫？

- 检查设备B是否在线（智控台设备状态）
- 确认设备B的固件已正确集成远程唤醒工具
- 检查MQTT网关连接是否正常
- 验证双向权限配置是否完整

### Q: 提示"无呼叫权限"？

- 在智控台确认设备A已勾选设备B的呼叫权限
- 确认配置已保存（非仅修改未保存）

### Q: 如何确认通讯录功能已开启？

- 智控台顶部菜单如显示"通讯录"入口，则表示已开启

### Q: 我叫他呼叫"张山"，但是他老是识别成"张三"，怎么办？
- 可以查阅你使用的asr服务的文档，确认是否支持热词识别。
- 如果你用的是`FunASRServer`,可以在容器里的`热词文件`里添加"张山"，然后重启容器。
- 如果你用的是`火山引擎`的服务，可以在`火山引擎的控制台`里添加`热词文件`，然后回到智控台的`模型配置页面`，把`热词文件名称`配置在`火山引擎的tts`上去。

