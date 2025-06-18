[![Banners](docs/images/banner1.png)](https://github.com/xinnan-tech/xiaozhi-esp32-server)

<h1 align="center">Xiaozhi Backend Service xiaozhi-esp32-server</h1>

<p align="center">
This project provides backend services for the open-source smart hardware project
<a href="https://github.com/78/xiaozhi-esp32">xiaozhi-esp32</a><br/>
Implemented using Python, Java, and Vue according to the <a href="https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh">Xiaozhi Communication Protocol</a><br/>
Helps you quickly set up your Xiaozhi server
</p>

<p align="center">
<a href="./README.md">中文</a>
· <a href="./docs/FAQ.md">FAQ</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/issues">Report Issues</a>
· <a href="./README_en.md#deployment-documentation">Deployment Guide</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">Release Notes</a>
</p>
<p align="center">
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/v/release/xinnan-tech/xiaozhi-esp32-server?logo=docker" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/graphs/contributors">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/contributors/xinnan-tech/xiaozhi-esp32-server?logo=github" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/xinnan-tech/xiaozhi-esp32-server?color=0088ff" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/pulls">
    <img alt="GitHub pull requests" src="https://img.shields.io/github/issues-pr/xinnan-tech/xiaozhi-esp32-server?color=0088ff" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/LICENSE">
    <img alt="GitHub pull requests" src="https://img.shields.io/badge/license-MIT-white?labelColor=black" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server">
    <img alt="stars" src="https://img.shields.io/github/stars/xinnan-tech/xiaozhi-esp32-server?color=ffcb47&labelColor=black" />
  </a>
</p>

---

## Target Users 👥

This project requires ESP32 hardware devices. If you have purchased ESP32-related hardware, successfully connected to Brother Xia's backend service, and want to set up your own `xiaozhi-esp32` backend service, then this project is perfect for you.

Want to see it in action? Check out these videos 🎥

<table>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1FMFyejExX" target="_blank">
         <picture>
           <img alt="Xiaozhi esp32 connecting to own backend model" src="docs/images/demo1.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1CDKWemEU6" target="_blank">
         <picture>
           <img alt="Custom voice" src="docs/images/demo2.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV12yA2egEaC" target="_blank">
         <picture>
           <img alt="Using Cantonese" src="docs/images/demo3.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1pNXWYGEx1" target="_blank">
         <picture>
           <img alt="Control home appliances" src="docs/images/demo5.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1kgA2eYEQ9" target="_blank">
         <picture>
           <img alt="Lowest cost configuration" src="docs/images/demo4.png" />
         </picture>
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1Vy96YCE3R" target="_blank">
         <picture>
           <img alt="Custom voice" src="docs/images/demo6.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1VC96Y5EMH" target="_blank">
         <picture>
           <img alt="Play music" src="docs/images/demo7.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1Z8XuYZEAS" target="_blank">
         <picture>
           <img alt="Weather plugin" src="docs/images/demo8.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV178XuYfEpi" target="_blank">
         <picture>
           <img alt="IOT command control" src="docs/images/demo9.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV17LXWYvENb" target="_blank">
         <picture>
           <img alt="News broadcast" src="docs/images/demo0.png" />
         </picture>
        </a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://www.bilibili.com/video/BV12J7WzBEaH" target="_blank">
         <picture>
           <img alt="Real-time interruption" src="docs/images/demo10.png" />
         </picture>
        </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1Co76z7EvK" target="_blank">
         <picture>
           <img alt="Photo recognition" src="docs/images/demo12.png" />
         </picture>
        </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1TJ7WzzEo6" target="_blank">
         <picture>
           <img alt="Multi-command tasks" src="docs/images/demo11.png" />
         </picture>
        </a>
    </td>
    <td>
    </td>
    <td>
    </td>
  </tr>
</table>

---

## Warning ⚠️

1. This project is open-source software. This software has no commercial relationship with any third-party API service providers (including but not limited to speech recognition, large models, speech synthesis, and other platforms) and does not provide any form of guarantee for their service quality or financial security.
It is recommended that users prioritize service providers with relevant business licenses and carefully read their service agreements and privacy policies. This software does not host any account keys, does not participate in fund transfers, and does not bear the risk of recharge fund losses.

2. This project's functionality is not complete and has not passed network security testing. Please do not use it in production environments. If you deploy this project for learning in a public network environment, please ensure necessary protection measures are in place.

---

## Deployment Documentation

![Banners](docs/images/banner2.png)

This project provides two deployment methods. Please choose according to your specific needs:

#### 🚀 Deployment Method Selection
| Deployment Method | Features | Suitable Scenarios | Deployment Guide | Requirements | Video Tutorial | 
|---------|------|---------|---------|---------|---------|
| **Simplified Installation** | Smart dialogue, IOT functionality, data stored in configuration files | Low-configuration environment, no database needed | [Docker Version](./docs/Deployment.md#method-1-docker-server-only) / [Source Code Deployment](./docs/Deployment.md#method-2-local-source-code-server-only) | 2 cores 4G if using `FunASR`, 2 cores 2G if using all APIs | - | 
| **Full Module Installation** | Smart dialogue, IOT, OTA, Control Panel, data stored in database | Complete functionality experience | [Docker Version](./docs/Deployment_all.md#method-1-docker-full-modules) / [Source Code Deployment](./docs/Deployment_all.md#method-2-local-source-code-full-modules) | 4 cores 8G if using `FunASR`, 2 cores 4G if using all APIs | [Local Source Code Startup Video Tutorial](https://www.bilibili.com/video/BV1wBJhz4Ewe) / [Local Source Code Auto-Update Tutorial](./docs/dev-ops-integration.md) | 

> 💡 Note: Below are the test platforms deployed with the latest code. You can flash and test if needed. Concurrent users: 6, data will be cleared daily

```
Control Panel Address: https://2662r3426b.vicp.fun

Service Test Tool: https://2662r3426b.vicp.fun/test/
OTA Interface Address: https://2662r3426b.vicp.fun/xiaozhi/ota/
Websocket Interface Address: wss://2662r3426b.vicp.fun/xiaozhi/v1/
```

#### 🚩 Configuration Description and Recommendations
> [!Note]
> The default configuration of this project is `Entry Level Free` settings. For better results, we recommend using `Full Streaming Configuration`.
> 
> Since version `0.5.2`, this project supports full streaming throughout the entire lifecycle. Compared to versions before `0.5`, response speed has improved by approximately `2.5 seconds`

| Module Name | Entry Level Free Settings | Full Streaming Configuration |
|---------|---------|------|
| ASR(Speech Recognition) | FunASR(Local) | ✅DoubaoASR(Volcano Streaming Speech Recognition) |
| LLM(Large Language Model) | ChatGLMLLM(Zhipu glm-4-flash) | ✅DoubaoLLM(Volcano doubao-1-5-pro-32k-250115) |
| VLLM(Vision Large Model) | ChatGLMVLLM(Zhipu glm-4v-flash) | ✅ChatGLMVLLM(Zhipu glm-4v-flash) |
| TTS(Speech Synthesis) | EdgeTTS(Microsoft Speech) | ✅HuoshanDoubleStreamTTS(Volcano Double Streaming Speech Synthesis) |
| Intent(Intent Recognition) | function_call(Function Call) | ✅function_call(Function Call) |
| Memory(Memory Function) | mem_local_short(Local Short-term Memory) | ✅mem_local_short(Local Short-term Memory) |

---
## Feature List ✨
### Implemented ✅

| Feature Module | Description |
|---------|------|
| Communication Protocol | Based on `xiaozhi-esp32` protocol, implements data interaction through WebSocket |
| Dialogue Interaction | Supports wake-up dialogue, manual dialogue, and real-time interruption. Auto-sleep after long periods of no dialogue |
| Intent Recognition | Supports LLM intent recognition, function call, reducing hard-coded intent judgment |
| Multi-language Recognition | Supports Mandarin, Cantonese, English, Japanese, Korean (default using FunASR) |
| LLM Module | Supports flexible LLM module switching, default using ChatGLMLLM, can also use Ali Bailian, DeepSeek, Ollama, etc. |
| TTS Module | Supports EdgeTTS (default), Volcano Engine Doubao TTS, and other TTS interfaces |
| Memory Function | Supports ultra-long memory, local summary memory, and no memory modes |
| IOT Function | Supports managing registered device IOT functionality, supports smart IoT control based on dialogue context |
| Control Panel | Provides Web management interface, supports agent management, user management, system configuration, etc. |

### In Development 🚧

To learn about specific development progress, [click here](https://github.com/users/xinnan-tech/projects/3)

If you are a software developer, here is an [Open Letter to Developers](docs/contributor_open_letter.md). Welcome to join!

---

## Product Ecosystem 👬
Xiaozhi is an ecosystem. When using this product, you might also want to check out other excellent projects in this ecosystem

| Project Name | Project Address | Project Description |
|:---------------------|:--------|:--------|
| Xiaozhi Android Client | [xiaozhi-android-client](https://github.com/TOM88812/xiaozhi-android-client) | A Flutter-based Android and iOS voice dialogue application supporting real-time voice interaction and text dialogue. |
| Xiaozhi PC Client | [py-xiaozhi](https://github.com/Huang-junsen/py-xiaozhi) | This project provides a Python-based Xiaozhi AI client, allowing you to experience Xiaozhi AI's functionality through code even without physical hardware. |
| Xiaozhi Java Server | [xiaozhi-esp32-server-java](https://github.com/joey-zhou/xiaozhi-esp32-server-java) | The Java version of Xiaozhi open-source backend service is a Java-based open-source project.<br/>It includes both frontend and backend services, aiming to provide users with a complete backend service solution. |

---

## Supported Platforms/Components List 📋

### LLM Language Models

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| openai interface call | Ali Bailian, Volcano Engine Doubao, DeepSeek, Zhipu ChatGLM, Gemini | Zhipu ChatGLM, Gemini |
| ollama interface call | Ollama | - |
| dify interface call | Dify | - |
| fastgpt interface call | Fastgpt | - |
| coze interface call | Coze | - |

In fact, any LLM that supports openai interface calls can be integrated and used.

### TTS Speech Synthesis

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| API Call | EdgeTTS, Volcano Engine Doubao TTS, Tencent Cloud, Alibaba Cloud TTS, CosyVoiceSiliconflow, TTS302AI, CozeCnTTS, GizwitsTTS, ACGNTTS, OpenAITTS | EdgeTTS, CosyVoiceSiliconflow(partial) |
| Local Service | FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3, MinimaxTTS | FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3, MinimaxTTS |

---

### VAD Voice Activity Detection

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:---:|:---------:|:----:|:----:|:--:|
| VAD | SileroVAD | Local Usage | Free | |

---

### ASR Speech Recognition

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Local Usage | FunASR, SherpaASR | FunASR, SherpaASR |
| API Call | DoubaoASR, FunASRServer, TencentASR, AliyunASR, GroqASR | FunASRServer |

---

### Memory Storage

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:------:|:---------------:|:----:|:---------:|:--:|
| Memory | mem0ai | API Call | 1000 calls/month quota | |
| Memory | mem_local_short | Local Summary | Free | |

---

### Intent Recognition

| Type | Platform Name | Usage Method | Pricing Model | Notes |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Intent | intent_llm | API Call | Based on LLM pricing | Uses large model for intent recognition, highly versatile |
| Intent | function_call | API Call | Based on LLM pricing | Uses large model function calls for intent, fast and effective |

---

## Acknowledgments 🙏

| Logo | Project/Company | Description |
|:---:|:---:|:---|
| <img src="./docs/images/logo_bailing.png" width="160"> | [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) | This project was inspired by [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) and implemented based on it |
| <img src="./docs/images/logo_tenclass.png" width="160"> | [Tenclass](https://www.tenclass.com/) | Thanks to [Tenclass](https://www.tenclass.com/) for establishing standard communication protocols, multi-device compatibility solutions, and high-concurrency scenario practices for the Xiaozhi ecosystem; providing full-chain technical documentation support for this project |
| <img src="./docs/images/logo_xuanfeng.png" width="160"> | [Xuanfeng Technology](https://github.com/Eric0308) | Thanks to [Xuanfeng Technology](https://github.com/Eric0308) for contributing the function call framework, MCP communication protocol, and plugin call mechanism implementation code, significantly improving front-end device (IoT) interaction efficiency and functional extensibility through standardized instruction scheduling system and dynamic expansion capabilities |
| <img src="./docs/images/logo_huiyuan.png" width="160"> | [Huiyuan Design](http://ui.kwd988.net/) | Thanks to [Huiyuan Design](http://ui.kwd988.net/) for providing professional visual solutions for this project, empowering the product user experience with their design experience serving over a thousand enterprises |
| <img src="./docs/images/logo_qinren.png" width="160"> | [Xi'an Qinren Information Technology](https://www.029app.com/) | Thanks to [Xi'an Qinren Information Technology](https://www.029app.com/) for deepening the visual system of this project, ensuring consistency and extensibility of the overall design style in multi-scenario applications |


<a href="https://star-history.com/#xinnan-tech/xiaozhi-esp32-server&Date">

 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>
