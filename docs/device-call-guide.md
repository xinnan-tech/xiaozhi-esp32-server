# Inter-device mutual call plugin usage guide

## Overview

The device call feature enables bidirectional communication between two configured devices via voice/data channels. When Device A calls Device B, the system follows this process:

```
Device A → Authorization Check → MQTT Gateway → Remote Wake-up of Device B → Connection Established → Call Established
```
## Prerequisites for using this feature
1. You must have at least two devices, each of model `ESP32-S3`, because only `ESP32-S3` supports remote wake-up.
2. Your device must have `two microphones`. If your device has only a `single microphone`, you can still try this feature, but expect significant lag.
3. You must use [Full Module Deployment](Deployment_all.md) for this project, as you need the `Console` to manage device permissions and communication.
4. You must install and configure the [MQTT Gateway Service ](mqtt-gateway-integration.md) after `May 27, 2026`. If you have already deployed the MQTT Gateway Service, ensure the code version is after `May 27, 2026`.

These are the mandatory prerequisites for using this feature. Detailed instructions follow.

## Configuration steps

### Step 1: Enable the contacts feature

1. Ensure your Console version is `0.9.4` or higher.
2. Log in to the Console backend
3. Go to **System Function Config**
4. Check the **Contacts** option in the left-side feature list
5. Click **Save Configuration** to confirm

### Step 2: Configure inter-device call permissions

1. Click **Contacts** in the top menu of the Console
2. Under the Agent list on the left, select Device A from the device list (search by MAC address or remark name).
3. In the right-side details panel, find the nickname setting for target device B, e.g., **"Xiao Wang"**
4. Check the **Call Permission** checkbox for Device B
5. Click **Save**

**Bidirectional Authorization Note:** To enable communication between Device A and Device B, configure mutual permissions in the Console on both sides. For example:

- Check device B in device A's config → Device A can communicate with device B
- Check device A in device B's config → Device B can communicate with device A

### Step 3: Add the call tool in the Agent config

1. Click **Agent Management** in the top menu of the Console
2. In the Agent associated with the recently configured device contact, click **Edit Role**
3. In the right-side details panel, click **Edit Features**
4. Check the **Device-to-Device Call** tool
5. Click **Save Configuration** to confirm
6. Click **Save Config** again on the outer layer, then restart the device

### Step 4: Add the remote wake-up tool on the firmware side

1. Add the remote wake-up tool MCP to the [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) codebase. Supported versions are 2.1.0 to 2.2.6 (version from May 29, 2026).
2. Add the remote wake-up function declaration in application.h
    ```cpp
    void RemoteWakeup(const std::string& reason);
    ```
3. Add the remote wake-up function in application.cc
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
4. Add the remote wake-up tool in mcp_server.cc
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
5. Complete firmware flashing according to the [Firmware Compilation and Flashing Guide](firmware-build.md)
6. Regardless of whether your device has a single or dual microphone, enable the AEC feature during compilation!
7. Regardless of whether your device has a single or dual microphone, enable the AEC feature during compilation!
8. Regardless of whether your device has a single or dual microphone, enable the AEC feature during compilation!

### Step 5: Configure the MQTT gateway service

1. Deploy the MQTT Gateway Service. Refer to [MQTT Gateway Integration Documentation](mqtt-gateway-integration.md)
2. If already deployed, confirm the code version is from May 27, 2026

## Call flow description

Prepare two devices. After configuring communication permissions in the Console and adding the call tool to the Agent, say "Call XXX" to one Xiaozhi device and observe if Device B responds.

## FAQ

### Q: Device B does not respond to the call?

- Check if Device B is online (Console device status)
- Ensure Device B's firmware correctly integrates the remote wake-up tool
- Check if the MQTT gateway connection is normal
- Verify if the bidirectional permission config is complete

### Q: Prompt shows "No call permission"?

- Verify in the Console that Device A has granted call permissions to Device B
- Ensure the configuration is saved (not just modified)

### Q: How to confirm the contacts feature is enabled?

- If the "Contacts" entry appears in the top menu of the Console, the feature is enabled

### Q: I ask it to call "Zhang Shan", but it always recognizes it as "Zhang San". What should I do?
- Check the documentation for your ASR service to confirm if hotword recognition is supported.
- If you use `FunASRServer`, add "Zhang Shan" to the `hotword file` in the container, then restart the container.
- If you use `Volcano Engine` services, add a `hotword file` in the `Volcano Engine Console`, then go to the `Model Configuration page` in the Console and configure the `hotword file name` for `Volcano Engine TTS`.

