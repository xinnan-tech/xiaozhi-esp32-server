# FAQ❓

### 1. Why does Xiaozhi recognize a lot of Korean, Japanese, and English when I speak? 🇰🇷

Suggestion: Check if `models/SenseVoiceSmall` already has `model.pt`
If you don't have the file, you need to download it. See here [Download the speech recognition model file](Deployment.md#Model file)

### 2. Why does "TTS task error file does not exist" appear? 📁

Suggestion: Check whether `conda` is used to install `libopus` and `ffmpeg` libraries correctly.

If not installed, install it

```
conda install conda-forge::libopus
conda install conda-forge::ffmpeg
```

### 3. TTS often fails and times out ⏰

Recommendation: If `EdgeTTS` frequently fails, please check whether you are using a proxy (router). If so, try disabling the proxy and try again.  
If you are using Doubao TTS with Volcano Engine and it often fails, it is recommended to use the paid version because the test version only supports 2 concurrent users.

### 4. I can connect to my own server using Wifi, but I can't connect using 4G mode🔐

Reason: In Xia Ge's firmware, 4G mode requires a secure connection.

Solution: There are currently two solutions. Choose one:

1. Change the code. Refer to this video to solve the problem https://www.bilibili.com/video/BV18MfTYoE85

2. Use nginx to configure SSL certificate. Refer to the tutorial https://icnt94i5ctj4.feishu.cn/docx/GnYOdMNJOoRCljx1ctecsj9cnRe

### 5. How to improve Xiaozhi's dialogue response speed? ⚡

The default configuration of this project is a low-cost solution. It is recommended that beginners use the default free model first to solve the problem of "running well" and then optimize the "running fast".  
If you need to improve response speed, you can try replacing various components. Since version 0.5.2, the project supports streaming configuration, which improves response speed by about 2.5 seconds compared to earlier versions, significantly improving the user experience.

| Module Name | Get Started with Free Setup | Streaming Configuration |
|:---:|:---:|:---:|
| ASR (Speech Recognition) | FunASR (Local) | 👍FunASR (Local GPU Mode) |
| LLM (Large Model) | ChatGLMLLM (Zhipuglm-4-flash) | 👍AliLLM (qwen3-235b-a22b-instruct-2507) or 👍DoubaoLLM (doubao-1-5-pro-32k-250115) |
| VLLM (Visual Large Model) | ChatGLMVLLM (Zhipu glm-4v-flash) | 👍QwenVLVLLM (Qianwen qwen2.5-vl-3b-instructh) |
| TTS (Text-to-Speech) | ✅LinkeraiTTS (Lingxi Streaming) | 👍HuoshanDoubleStreamTTS (Huoshan Double Stream Text-to-Speech) or 👍AliyunStreamTTS (Aliyun Stream Text-to-Speech) |
| Intent (intent recognition) | function_call (function call) | function_call (function call) |
| Memory (memory function) | mem_local_short (local short-term memory) | mem_local_short (local short-term memory) |

If you are concerned about the time consumption of each component, please refer to the [Xiaozhi Component Performance Test Report](https://github.com/xinnan-tech/xiaozhi-performance-research) and conduct actual tests in your environment according to the test methods in the report.

### 6. I speak very slowly, and when I pause, Xiaozhi always interrupts me.

Suggestion: Find the following section in the configuration file and increase the value of `min_silence_duration_ms` (for example, to `1000`):

```yaml
VAD:
  SileroVAD:
    threshold: 0.5
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 700 # If the pauses in speaking are long, you can increase this value
```

### 7. Deployment related tutorials
1. [How to perform the simplest deployment](./Deployment.md)
2. [How to deploy all modules](./Deployment_all.md)<br/>
2. [How to deploy an MQTT gateway and enable the MQTT+UDP protocol](./mqtt-gateway-integration.md)
3. [How to automatically pull the latest code of this project, compile and start it](./dev-ops-integration.md)<br/>
4. [How to integrate with Nginx](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)

### 8. Compile firmware related tutorials
1. [How to compile Xiaozhi firmware yourself](./firmware-build.md)<br/>
2. [How to modify the OTA address based on the firmware compiled by Xia Ge](./firmware-setting.md)<br/>

### 8. Expand related tutorials
1. [How to enable mobile phone number registration smart console](./ali-sms-integration.md)<br/>
2. [How to integrate HomeAssistant to achieve smart home control](./homeassistant-integration.md)
3. [How to enable the vision model to realize photo recognition](./mcp-vision-integration.md)
4. [How to deploy MCP access points](./mcp-endpoint-enable.md)
5. [How to access the MCP access point](./mcp-endpoint-integration.md)
6. [How to enable voiceprint recognition](./voiceprint-integration.md)
10. [News plugin source configuration guide](./newsnow_plugin_config.md)<br/>

### 9. Tutorials on voice cloning and local voice deployment
1. [How to deploy and integrate index-tts local voice](./index-stream-integration.md)<br/>
2. [How to deploy integrated fish-speech local voice](./fish-speech-integration.md)<br/>
3. [How to deploy and integrate PaddleSpeech local voice](./paddlespeech-deploy.md)<br/>

### 10. Performance Testing Tutorial
1. [Component Speed ​​Test Guide](./performance_tester.md)<br/>
2. [Publish test results regularly](https://github.com/xinnan-tech/xiaozhi-performance-research)

### 13. For more questions, please contact us for feedback💬

Please submit your issues at [issues](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues).
