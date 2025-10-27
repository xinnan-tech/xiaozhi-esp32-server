# 常见问题 ❓

### 1、为什么我说的话，小智识别出来很多韩文、日文、英文？🇰🇷

建议：检查一下`models/SenseVoiceSmall`是否已经有`model.pt`
文件，如果没有就要下载，查看这里[下载语音识别模型文件](Deployment.md#模型文件)

### 2、为什么会出现"TTS 任务出错 文件不存在"？📁

建议：检查一下是否正确使用`conda` 安装了`libopus`和`ffmpeg`库。

如果没有安装，就安装

```
conda install conda-forge::libopus
conda install conda-forge::ffmpeg
```

### 3、TTS 经常失败，经常超时 ⏰

建议：如果 `EdgeTTS` 经常失败，请先检查是否使用了代理（梯子）。如果使用了，请尝试关闭代理后再试；  
如果用的是火山引擎的豆包 TTS，经常失败时建议使用付费版本，因为测试版本仅支持 2 个并发。

### 4、使用Wifi能连接自建服务器，但是4G模式却接不上 🔐

原因：虾哥的固件，4G模式需要使用安全连接。

解决方法：目前有两种方法可以解决。任选一种：

1、改代码。参考这个视频解决 https://www.bilibili.com/video/BV18MfTYoE85

2、使用nginx配置ssl证书。参考教程 https://icnt94i5ctj4.feishu.cn/docx/GnYOdMNJOoRCljx1ctecsj9cnRe

### 5、如何提高小智对话响应速度？ ⚡

本项目默认配置为低成本方案，建议初学者先使用默认免费模型，解决"跑得动"的问题，再优化"跑得快"。  
如需提升响应速度，可尝试更换各组件。自`0.5.2`版本起，项目支持流式配置，相比早期版本，响应速度提升约`2.5秒`，显著改善用户体验。

| 模块名称 | 入门全免费设置 | 流式配置 |
|:---:|:---:|:---:|
| ASR(语音识别) | FunASR(本地) | 👍FunASR(本地GPU模式) |
| LLM(大模型) | ChatGLMLLM(智谱glm-4-flash) | 👍AliLLM(qwen3-235b-a22b-instruct-2507) 或 👍DoubaoLLM(doubao-1-5-pro-32k-250115) |
| VLLM(视觉大模型) | ChatGLMVLLM(智谱glm-4v-flash) | 👍QwenVLVLLM(千问qwen2.5-vl-3b-instructh) |
| TTS(语音合成) | ✅LinkeraiTTS(灵犀流式) | 👍HuoshanDoubleStreamTTS(火山双流式语音合成) 或 👍AliyunStreamTTS(阿里云流式语音合成) |
| Intent(意图识别) | function_call(函数调用) | function_call(函数调用) |
| Memory(记忆功能) | mem_local_short(本地短期记忆） | mem_local_short（本地短期记忆） |

如果您关心各组件的耗时，请查阅[小智各组件性能测试报告](https://github.com/xinnan-tech/xiaozhi-performance-research)，可按报告中的测试方法在您的环境中实际测试。

### 6、我说话很慢，停顿时小智老是抢话 🗣️

建议：在配置文件中找到如下部分，将 `min_silence_duration_ms` 的值调大（例如改为 `1000`）：

```yaml
VAD:
  SileroVAD:
    threshold: 0.5
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 700  # 如果说话停顿较长，可将此值调大
```

### 7、部署相关教程
1、[如何进行最简化部署](./Deployment.md)<br/>
2、[如何进行全模块部署](./Deployment_all.md)<br/>
2、[如何部署MQTT网关开启MQTT+UDP协议](./mqtt-gateway-integration.md)<br/>
3、[如何自动拉取本项目最新代码自动编译和启动](./dev-ops-integration.md)<br/>
4、[如何与Nginx集成](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)<br/>

### 8、编译固件相关教程
1、[如何自己编译小智固件](./firmware-build.md)<br/>
2、[如何基于虾哥编译好的固件修改OTA地址](./firmware-setting.md)<br/>

### 8、拓展相关教程
1、[如何开启手机号码注册智控台](./ali-sms-integration.md)<br/>
2、[如何集成HomeAssistant实现智能家居控制](./homeassistant-integration.md)<br/>
3、[如何开启视觉模型实现拍照识物](./mcp-vision-integration.md)<br/>
4、[如何部署MCP接入点](./mcp-endpoint-enable.md)<br/>
5、[如何接入MCP接入点](./mcp-endpoint-integration.md)<br/>
6、[如何开启声纹识别](./voiceprint-integration.md)<br/>
7、[新闻插件源配置指南](./newsnow_plugin_config.md)<br/>
8、[如何通过MCP传递设备ID（MAC地址）信息](./mcp-device_id-transfer.md)<br/>

### 9、语音克隆、本地语音部署相关教程
1、[如何在智控台克隆音色](./huoshan-streamTTS-voice-cloning.md)<br/>
2、[如何部署集成index-tts本地语音](./index-stream-integration.md)<br/>
3、[如何部署集成fish-speech本地语音](./fish-speech-integration.md)<br/>
4、[如何部署集成PaddleSpeech本地语音](./paddlespeech-deploy.md)<br/>

### 10、性能测试教程
1、[各组件速度测试指南](./performance_tester.md)<br/>
2、[定期公开测试结果](https://github.com/xinnan-tech/xiaozhi-performance-research)<br/>

### 13、更多问题，可联系我们反馈 💬

可以在[issues](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues)提交您的问题。