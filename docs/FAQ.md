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

### 7、部署相关教程
1、[如何进行最简化部署](./Deployment.md)<br/>
2、[如何进行全模块部署](./Deployment_all.md)<br/>
3、[如何部署MQTT网关开启MQTT+UDP协议](./mqtt-gateway-integration.md)<br/>
4、[如何自动拉取本项目最新代码自动编译和启动](./dev-ops-integration.md)<br/>
5、[如何与Nginx集成](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)<br/>

### 9、编译固件相关教程
1、[如何自己编译小智固件](./firmware-build.md)<br/>
2、[如何基于虾哥编译好的固件修改OTA地址](./firmware-setting.md)<br/>

### 10、拓展相关教程
1、[如何开启手机号码注册智控台](./ali-sms-integration.md)<br/>
2、[如何集成HomeAssistant实现智能家居控制](./homeassistant-integration.md)<br/>
3、[如何开启视觉模型实现拍照识物](./mcp-vision-integration.md)<br/>
4、[如何部署MCP接入点](./mcp-endpoint-enable.md)<br/>
5、[如何接入MCP接入点](./mcp-endpoint-integration.md)<br/>
6、[MCP方法如何获取设备信息](./mcp-get-device-info.md)<br/>
7、[如何开启声纹识别](./voiceprint-integration.md)<br/>
8、[新闻插件源配置指南](./newsnow_plugin_config.md)<br/>
9、[知识库ragflow集成指南](./ragflow-integration.md)<br/>

### 11、语音克隆、本地语音部署相关教程
1、[如何在智控台克隆音色](./huoshan-streamTTS-voice-cloning.md)<br/>
2、[如何部署集成index-tts本地语音](./index-stream-integration.md)<br/>
3、[如何部署集成fish-speech本地语音](./fish-speech-integration.md)<br/>
4、[如何部署集成PaddleSpeech本地语音](./paddlespeech-deploy.md)<br/>

### 12、性能测试教程
1、[各组件速度测试指南](./performance_tester.md)<br/>
2、[定期公开测试结果](https://github.com/xinnan-tech/xiaozhi-performance-research)<br/>

### 13、更多问题，可联系我们反馈 💬

可以在[issues](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues)提交您的问题。
