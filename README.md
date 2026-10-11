<h1 align="center">Xiaozhi Backend Service xiaozhi-esp32-server</h1>

<p align="center">
This project is based on human-machine symbiotic intelligence theory and technology to develop intelligent terminal hardware and software systems<br/>providing backend services for the open-source intelligent hardware project
<a href="https://github.com/78/xiaozhi-esp32">xiaozhi-esp32</a><br/>
Implemented using Python, Java, and Vue according to the <a href="https://github.com/lapy/xiaozhi-esp32-server/wiki">Xiaozhi Communication Protocol</a><br/>
Supports MCP endpoints and voiceprint recognition
</p>

<p align="center">
<a href="./docs/support/faq.md">FAQ</a>
· <a href="https://github.com/lapy/xiaozhi-esp32-server/issues">Report Issues</a>
· <a href="https://github.com/lapy/xiaozhi-esp32-server/releases">Release Notes</a>
</p>
<p align="center">
  <a href="https://github.com/lapy/xiaozhi-esp32-server/releases">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/v/release/lapy/xiaozhi-esp32-server?logo=docker" />
  </a>
  <a href="https://github.com/lapy/xiaozhi-esp32-server/graphs/contributors">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/contributors/lapy/xiaozhi-esp32-server?logo=github" />
  </a>
  <a href="https://github.com/lapy/xiaozhi-esp32-server/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/lapy/xiaozhi-esp32-server?color=0088ff" />
  </a>
  <a href="https://github.com/lapy/xiaozhi-esp32-server/pulls">
    <img alt="GitHub pull requests" src="https://img.shields.io/github/issues-pr/lapy/xiaozhi-esp32-server?color=0088ff" />
  </a>
  <a href="https://github.com/lapy/xiaozhi-esp32-server/blob/main/LICENSE">
    <img alt="GitHub pull requests" src="https://img.shields.io/badge/license-MIT-white?labelColor=black" />
  </a>
  <a href="https://github.com/lapy/xiaozhi-esp32-server">
    <img alt="stars" src="https://img.shields.io/github/stars/lapy/xiaozhi-esp32-server?color=ffcb47&labelColor=black" />
  </a>
</p>


---

## ⚠️ Important Disclaimer

**This is a complete port and refactoring of the original [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) project, specifically adapted for Western users.**

### Credits & Acknowledgments
- **Original Project**: All credits for the original excellent work go to the [xinnan-tech](https://github.com/xinnan-tech) team
- **Original Repository**: [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
- **This Port**: Adapted by [lapy](https://github.com/lapy) for Western users

### What Changed
This port removes Chinese AI providers and infrastructure dependencies, replacing them with Western alternatives:
- **STT**: WhisperASR (offline, multilingual) instead of Chinese ASR services
- **LLM**: LMStudioLLM (local, open-source) instead of Chinese LLM providers
- **TTS**: EdgeTTS (Microsoft, free) - kept as default
- **Infrastructure**: Replaced Chinese mirrors with international alternatives
- **Documentation**: Translated and adapted for Western users

The core architecture, ESP32 communication protocol, and fundamental functionality remain unchanged from the original excellent work.

---

## Target Users 👥

This project requires ESP32 hardware devices to work. If you have purchased ESP32-related hardware, successfully connected to Brother Xia's deployed backend service, and want to build your own `xiaozhi-esp32` backend service independently, then this project is perfect for you.

---

## Warnings ⚠️

1. This project is open-source software. This software has no commercial partnership with any third-party API service providers (including but not limited to speech recognition, large models, speech synthesis, and other platforms) that it interfaces with, and does not provide any form of guarantee for their service quality or financial security. It is recommended that users prioritize service providers with relevant business licenses and carefully read their service agreements and privacy policies. This software does not host any account keys, does not participate in fund flows, and does not bear the risk of recharge fund losses.

2. The functionality of this project is not complete and has not passed network security assessment. Please do not use it in production environments. If you deploy this project for learning purposes in a public network environment, please ensure necessary protection measures are in place.

---

## Deployment Documentation

This project provides two deployment methods. Please choose based on your specific needs:

#### 🚀 Deployment Method Selection
| Deployment Method | Features | Applicable Scenarios | Deployment Docs | Configuration Requirements | Video Tutorials |
|---------|------|---------|---------|---------|---------|
| **Simplified Installation** | Intelligent dialogue, IOT, MCP, visual perception | Low-configuration environments, data stored in config files, no database required | [①Docker Version](./docs/installation/docker.md) / [②Source Code Deployment](./docs/installation/local.md)| 2 cores 2GB if all APIs | - |
| **Full Module Installation** | Intelligent dialogue, IOT, MCP endpoints, voiceprint recognition, visual perception, OTA, intelligent control console | Complete functionality experience, data stored in database |[①Docker Version](./docs/installation/docker.md) / [②Source Code Deployment](./docs/installation/local.md) | 2 cores 4GB if all APIs| - |


> 💡 Note: Below is a test platform deployed with the latest code. You can burn and test if needed. Concurrent users: 6, data will be cleared daily.

```
Intelligent Control Console Address: https://2662r3426b.vicp.fun
Intelligent Control Console Address (H5): https://2662r3426b.vicp.fun/h5/index.html

Service Test Tool: https://2662r3426b.vicp.fun/test/
OTA Interface Address: https://2662r3426b.vicp.fun/xiaozhi/ota/
Websocket Interface Address: wss://2662r3426b.vicp.fun/xiaozhi/v1/
```

#### 🚩 Configuration Description and Recommendations
> [!Note]
> This project provides two configuration schemes:
>
> 1. `Entry Level Free Settings`: Suitable for personal and home use, all components use free solutions, no additional payment required.
>
> 2. `Streaming Configuration`: Suitable for demonstrations, training, scenarios with more than 2 concurrent users, etc. Uses streaming processing technology for faster response speed and better experience.
>
> Starting from version `0.5.2`, the project supports streaming configuration. Compared to earlier versions, response speed is improved by approximately `2.5 seconds`, significantly improving user experience.

| Module Name | Entry Level Free Settings | Streaming Configuration |
|:---:|:---:|:---:|
| ASR(Speech Recognition) | ✅WhisperASR(Local, Offline) | 👍WhisperASR(Local, Offline) |
| LLM(Large Model) | ✅LMStudioLLM(Local, Open Source) | 👍LMStudioLLM(Local, Open Source) |
| VLLM(Vision Large Model) | OpenAILLMVLLM(OpenAI gpt-4o) | 👍OpenAILLMVLLM(OpenAI gpt-4o) |
| TTS(Speech Synthesis) | ✅EdgeTTS(Microsoft Edge TTS) | 👍EdgeTTS(Microsoft Edge TTS) |
| Intent(Intent Recognition) | function_call(Function calling) | function_call(Function calling) |
| Memory(Memory function) | mem_local_short(Local short-term memory) | mem_local_short(Local short-term memory) |

#### 🔧 Testing Tools
This project provides the following testing tools to help you verify the system and choose suitable models:

| Tool Name | Location | Usage Method | Function Description |
|:---:|:---|:---:|:---:|
| Audio Interaction Test Tool | main/xiaozhi-server/test/test_page.html | Open directly with Google Chrome | Tests audio playback and reception functions, verifies if Python-side audio processing is normal |
| Model Response Test Tool 1 | main/xiaozhi-server/performance_tester.py | Execute `python performance_tester.py` | Tests response speed of three core modules: ASR(speech recognition), LLM(large model), TTS(speech synthesis) |
| Model Response Test Tool 2 | main/xiaozhi-server/performance_tester_vllm.py | Execute `python performance_tester_vllm.py` | Tests VLLM(vision model) response speed |

> 💡 Note: When testing model speed, only models with configured keys will be tested.

---
## Feature List ✨
### Implemented ✅
| Feature Module | Description |
|:---:|:---|
| Core Architecture | Based on [MQTT+UDP gateway](https://github.com/lapy/xiaozhi-esp32-server/blob/main/docs/guides/mqtt.md), WebSocket and HTTP servers, provides complete console management and authentication system |
| Voice Interaction | Supports streaming ASR(speech recognition), streaming TTS(speech synthesis), VAD(voice activity detection), supports multi-language recognition and voice processing |
| Voiceprint Recognition | Supports multi-user voiceprint registration, management, and recognition, processes in parallel with ASR, real-time speaker identity recognition and passes to LLM for personalized responses |
| Intelligent Dialogue | Supports multiple LLM(large language models), implements intelligent dialogue |
| Visual Perception | Supports multiple VLLM(vision large models), implements multimodal interaction |
| Intent Recognition | Supports LLM intent recognition, Function Call function calling, provides plugin-based intent processing mechanism |
| Memory System | Supports local short-term memory, mem0ai interface memory, with memory summarization functionality |
| Command Delivery | Supports MCP command delivery to ESP32 devices via MQTT protocol from Smart Console |
| Tool Calling | Supports client IOT protocol, client MCP protocol, server MCP protocol, MCP endpoint protocol, custom tool functions |
| Management Backend | Provides Web management interface, supports user management, system configuration and device management; Supports English display |
| Testing Tools | Provides performance testing tools, vision model testing tools, and audio interaction testing tools |
| Deployment Support | Supports Docker deployment and local deployment, provides complete configuration file management |
| Plugin System | Supports functional plugin extensions, custom plugin development, and plugin hot-loading |

### Under Development 🚧

If you are a software developer, here is our [Contributing Guide](docs/support/contributing.md). Welcome to join!

---

## Product Ecosystem 👬
Xiaozhi is an ecosystem. When using this product, you can also check out other [excellent projects](https://github.com/78/xiaozhi-esp32?tab=readme-ov-file#related-open-source-projects) in this ecosystem

| Project Name | Project Address | Project Description |
|:---------------------|:--------|:--------|
| Xiaozhi Android Client | [xiaozhi-android-client](https://github.com/TOM88812/xiaozhi-android-client) | An Android and iOS voice dialogue application based on xiaozhi-server, supporting real-time voice interaction and text dialogue.<br/>Currently a Flutter version, connecting iOS and Android platforms. |
| Xiaozhi Desktop Client | [py-xiaozhi](https://github.com/Huang-junsen/py-xiaozhi) | This project provides a Python-based AI client for beginners, allowing users to experience Xiaozhi AI functionality through code even without physical hardware conditions. |
| Xiaozhi Java Server | [xiaozhi-esp32-server-java](https://github.com/joey-zhou/xiaozhi-esp32-server-java) | Xiaozhi open-source backend service Java version is a Java-based open-source project.<br/>It includes frontend and backend services, aiming to provide users with a complete backend service solution. |

---

## Supported Platforms/Components List 📋
### LLM Language Models

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Local deployment | **LMStudioLLM**, OllamaLLM, XinferenceLLM | **LMStudioLLM**, OllamaLLM, XinferenceLLM |
| OpenAI interface calls | OpenAILLM | - |
| Google interface calls | GeminiLLM | GeminiLLM |
| Platform integrations | DifyLLM, HomeAssistant | - |

In fact, any LLM that supports OpenAI interface calls can be integrated and used, including Xinference and HomeAssistant interfaces.

---

### VLLM Vision Models

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| OpenAI interface calls | OpenAILLMVLLM | - |
| Google interface calls | GeminiVLLM | GeminiVLLM |

In fact, any VLLM that supports OpenAI interface calls can be integrated and used.

---

### TTS Speech Synthesis

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Interface calls | OpenAITTS, EdgeTTS | EdgeTTS |
| Local services | CustomTTS | CustomTTS |

---

### VAD Voice Activity Detection

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:---:|:---------:|:----:|:----:|:--:|
| VAD | SileroVAD | Local use | Free | |

---

### ASR Speech Recognition

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Local deployment | SherpaASR, VoskASR, **WhisperASR** | SherpaASR, VoskASR, **WhisperASR** |
| OpenAI interface calls | OpenaiASR, GroqASR | OpenaiASR, GroqASR |
| Google interface calls | GeminiASR | GeminiASR |

---

### Voiceprint Recognition

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| External HTTP service | Any voiceprint API compatible with the built-in `VoiceprintProvider` protocol (see [guide](./docs/guides/voiceprint.md)) | Self-hosted services |

---

### Memory Storage

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:------:|:---------------:|:----:|:---------:|:--:|
| Memory | **mem_local_short** | Local summarization | Free | Local short-term memory with LLM summarization |
| Memory | mem0ai | Interface calls | 1000 times/month quota | Cloud-based memory service |
| Memory | nomem | No memory | Free | Disables memory functionality |

---

### Intent Recognition

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Intent | **function_call** | Interface calls | Based on LLM pricing | Function calling through LLM, fast speed, good effect |
| Intent | intent_llm | Interface calls | Based on LLM pricing | Intent recognition through LLM, strong generalization |
| Intent | nointent | No intent | Free | Disables intent recognition |

---

## Acknowledgments 🙏

| Logo | Project/Company | Description |
|:---:|:---:|:---|
| 🎤 | [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) | This project is inspired by [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) and implemented on its basis |
| 🏫 | [Tenclass](https://www.tenclass.com/) | Thanks to [Tenclass](https://www.tenclass.com/) for formulating standard communication protocols, multi-device compatibility solutions, and high-concurrency scenario practice demonstrations for the Xiaozhi ecosystem; providing full-link technical documentation support for this project |
| 🌪️ | [Xuanfeng Technology](https://github.com/Eric0308) | Thanks to [Xuanfeng Technology](https://github.com/Eric0308) for contributing function calling framework, MCP communication protocol, and plugin-based calling mechanism implementation code. Through standardized instruction scheduling system and dynamic expansion capabilities, it significantly improves the interaction efficiency and functional extensibility of frontend devices (IoT) |
| 📱 | [huangjunsen](https://github.com/huangjunsen0406) | Thanks to [huangjunsen](https://github.com/huangjunsen0406) for contributing the `Smart Control Console Mobile` module, which enables efficient control and real-time interaction across mobile devices, significantly enhancing the system's operational convenience and management efficiency in mobile scenarios. |
| 🎨 | [Huiyuan Design](http://ui.kwd988.net/) | Thanks to [Huiyuan Design](http://ui.kwd988.net/) for providing professional visual solutions for this project, using their design practical experience serving over a thousand enterprises to empower this project's product user experience |
| 🏢 | [Xi'an Qinren Information Technology](https://www.029app.com/) | Thanks to [Xi'an Qinren Information Technology](https://www.029app.com/) for deepening this project's visual system, ensuring consistency and extensibility of overall design style in multi-scenario applications |
| 👥 | [Code Contributors](https://github.com/lapy/xiaozhi-esp32-server/graphs/contributors) | Thanks to [all code contributors](https://github.com/lapy/xiaozhi-esp32-server/graphs/contributors), your efforts have made the project more robust and powerful. |


<a href="https://star-history.com/#lapy/xiaozhi-esp32-server&Date">

 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=lapy/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=lapy/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=lapy/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>
