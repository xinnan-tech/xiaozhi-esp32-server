[![Banners](docs/images/banner1.png)](https://github.com/xinnan-tech/xiaozhi-esp32-server)

<h1 align="center">小智后端服务xiaozhi-esp32-server</h1>

<p align="center">
本项目为开源智能硬件项目
<a href="https://github.com/78/xiaozhi-esp32">xiaozhi-esp32</a>提供后端服务<br/>
根据<a href="https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh">小智通信协议</a>使用Python、Java、Vue实现<br/>
帮助您快速搭建小智服务器
</p>

<p align="center">
<a href="./README_en.md">English</a>
· <a href="./docs/FAQ.md">常见问题</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/issues">反馈问题</a>
· <a href="./README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3">部署文档</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">更新日志</a>
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

## 适用人群 👥

本项目需要配合 ESP32 硬件设备使用。如果您已经购买了 ESP32 相关硬件，且成功对接过虾哥部署的后端服务，并希望独立搭建自己的
`xiaozhi-esp32` 后端服务，那么本项目非常适合您。

想看使用效果？请猛戳视频 🎥

<table>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1FMFyejExX" target="_blank">
         <picture>
           <img alt="小智esp32连接自己的后台模型" src="docs/images/demo1.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1CDKWemEU6" target="_blank">
         <picture>
           <img alt="自定义音色" src="docs/images/demo2.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV12yA2egEaC" target="_blank">
         <picture>
           <img alt="使用粤语交流" src="docs/images/demo3.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1pNXWYGEx1" target="_blank">
         <picture>
           <img alt="控制家电开关" src="docs/images/demo5.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1kgA2eYEQ9" target="_blank">
         <picture>
           <img alt="成本最低配置" src="docs/images/demo4.png" />
         </picture>
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1Vy96YCE3R" target="_blank">
         <picture>
           <img alt="自定义音色" src="docs/images/demo6.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1VC96Y5EMH" target="_blank">
         <picture>
           <img alt="播放音乐" src="docs/images/demo7.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1Z8XuYZEAS" target="_blank">
         <picture>
           <img alt="天气插件" src="docs/images/demo8.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV178XuYfEpi" target="_blank">
         <picture>
           <img alt="IOT指令控制设备" src="docs/images/demo9.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV17LXWYvENb" target="_blank">
         <picture>
           <img alt="播报新闻" src="docs/images/demo0.png" />
         </picture>
        </a>
    </td>
  </tr>
</table>

---

## 警告 ⚠️

1、本项目为开源软件，本软件与对接的任何第三方API服务商（包括但不限于语音识别、大模型、语音合成等平台）均不存在商业合作关系，不为其服务质量及资金安全提供任何形式的担保。
建议使用者优先选择持有相关业务牌照的服务商，并仔细阅读其服务协议及隐私政策。本软件不托管任何账户密钥、不参与资金流转、不承担充值资金损失风险。

2、本项目功能未完善，且未通过网络安全测评，请勿在生产环境中使用。 如果您在公网环境中部署学习本项目，请务必做好必要的防护。

---

## 部署文档

![Banners](docs/images/banner2.png)

本项目提供两种部署方式，请根据您的具体需求选择：

#### 🚀 部署方式选择

| 部署方式 | 特点 | 适用场景 | Docker部署文档 | 源码部署文档 |
|---------|------|---------|---------|---------|
| **最简化安装** | 智能对话、IOT功能，数据存储在配置文件 | 低配置环境，无需数据库 | [Docker只运行Server](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E5%8F%AA%E8%BF%90%E8%A1%8Cserver) | [本地源码只运行Server](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E5%8F%AA%E8%BF%90%E8%A1%8Cserver)|
| **全模块安装** | 智能对话、IOT、OTA、智控台，数据存储在数据库 | 完整功能体验 |[Docker运行全模块](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) | [本地源码运行全模块](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) |

> 💡 提示：以下是按最新代码部署后的测试平台，有需要可烧录测试，并发为6个，每天会清空数据

```
智控台地址: https://2662r3426b.vicp.fun

服务测试工具： https://2662r3426b.vicp.fun/test/
OTA接口地址: https://2662r3426b.vicp.fun/xiaozhi/ota/
Websocket接口地址: wss://2662r3426b.vicp.fun/xiaozhi/v1/
```

---
## 功能清单 ✨

### 已实现 ✅

| 功能模块 | 描述 |
|---------|------|
| 通信协议 | 基于 `xiaozhi-esp32` 协议，通过 WebSocket 实现数据交互 |
| 对话交互 | 支持唤醒对话、手动对话及实时打断。长时间无对话时自动休眠 |
| 意图识别 | 支持使用LLM意图识别、function call函数调用，减少硬编码意图判断 |
| 多语言识别 | 支持国语、粤语、英语、日语、韩语（默认使用 FunASR） |
| LLM 模块 | 支持灵活切换 LLM 模块，默认使用 ChatGLMLLM，也可选用阿里百炼、DeepSeek、Ollama 等接口 |
| TTS 模块 | 支持 EdgeTTS（默认）、火山引擎豆包 TTS 等多种 TTS 接口，满足语音合成需求 |
| 记忆功能 | 支持超长记忆、本地总结记忆、无记忆三种模式，满足不同场景需求 |
| IOT功能 | 支持管理注册设备IOT功能，支持基于对话上下文语境下的智能物联网控制 |
| 智控台 | 提供Web管理界面，支持智能体管理、用户管理、系统配置等功能，方便管理员和用户进行管理 |

### 正在开发 🚧

想了解具体开发计划进度，[请点击这里](https://github.com/users/xinnan-tech/projects/3)

如果你是一名软件开发者，这里有一份[《致开发者的公开信》](docs/contributor_open_letter.md)，欢迎加入！

---

## 产品生态 👬
小智是一个生态，当你使用这个产品时，也可以看看其他在这个生态圈的优秀项目

| 项目名称  | 项目地址 | 项目描述 |
|:---------------------|:--------|:--------|
| 小智安卓客户端  | [xiaozhi-android-client](https://github.com/TOM88812/xiaozhi-android-client) | 一个基于xiaozhi-server的Android、IOS语音对话应用,支持实时语音交互和文字对话。<br/>现在是flutter版本，打通IOS、Android端。 |
| 小智电脑客户端  | [py-xiaozhi](https://github.com/Huang-junsen/py-xiaozhi) | 该项目提供了一个基于 Python 实现的小白 AI 客户端，使得在不具备实体硬件条件的情况下，<br/>依然能够体过代码体验小智 AI 的功能。 |
| 小智Java服务端  | [xiaozhi-esp32-server-java](https://github.com/joey-zhou/xiaozhi-esp32-server-java) | 小智开源后端服务 Java 版本是一个基于 Java 的开源项目。<br/>它包括前后端的服务，旨在为用户提供一个完整的后端服务解决方案。 |

---

## 本项目支持的平台/组件列表 📋

### LLM 语言模型

| 使用方式 | 支持平台 | 免费平台 |
|:---:|:---:|:---:|
| openai 接口调用 | 阿里百炼、火山引擎豆包、深度求索、智谱ChatGLM、Gemini | 智谱ChatGLM、Gemini |
| ollama 接口调用 | Ollama | - |
| dify 接口调用 | Dify | - |
| fastgpt 接口调用 | Fastgpt | - |
| coze 接口调用 | Coze | - |

实际上，任何支持 openai 接口调用的 LLM 均可接入使用。

---

### TTS 语音合成

| 使用方式 | 支持平台 | 免费平台 |
|:---:|:---:|:---:|
| 接口调用 | EdgeTTS、火山引擎豆包TTS、腾讯云、阿里云TTS、CosyVoiceSiliconflow、TTS302AI、CozeCnTTS、GizwitsTTS、ACGNTTS、OpenAITTS | EdgeTTS、CosyVoiceSiliconflow(部分) |
| 本地服务 | FishSpeech、GPT_SOVITS_V2、GPT_SOVITS_V3、MinimaxTTS | FishSpeech、GPT_SOVITS_V2、GPT_SOVITS_V3、MinimaxTTS |

---

### VAD 语音活动检测

| 类型  |   平台名称    | 使用方式 | 收费模式 | 备注 |
|:---:|:---------:|:----:|:----:|:--:|
| VAD | SileroVAD | 本地使用 |  免费  |    |

---

### ASR 语音识别

| 使用方式 | 支持平台 | 免费平台 |
|:---:|:---:|:---:|
| 本地使用 | FunASR、SherpaASR | FunASR、SherpaASR |
| 接口调用 | DoubaoASR、FunASRServer、TencentASR、AliyunASR | FunASRServer |

---

### Memory 记忆存储

|   类型   |      平台名称       | 使用方式 |   收费模式    | 备注 |
|:------:|:---------------:|:----:|:---------:|:--:|
| Memory |     mem0ai      | 接口调用 | 1000次/月额度 |    |
| Memory | mem_local_short | 本地总结 |    免费     |    |

---

### Intent 意图识别

|   类型   |     平台名称      | 使用方式 |  收费模式   |          备注           |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Intent |  intent_llm   | 接口调用 | 根据LLM收费 |    通过大模型识别意图，通用性强     |
| Intent | function_call | 接口调用 | 根据LLM收费 | 通过大模型函数调用完成意图，速度快，效果好 |

---

## 鸣谢 🙏

| Logo | 项目/公司 | 说明 |
|:---:|:---:|:---|
| <img src="./docs/images/logo_bailing.png" width="160"> | [百聆语音对话机器人](https://github.com/wwbin2017/bailing) | 本项目受[百聆语音对话机器人](https://github.com/wwbin2017/bailing)启发，并在其基础上实现 |
| <img src="./docs/images/logo_tenclass.png" width="160"> | [十方融海](https://www.tenclass.com/) | 感谢[十方融海](https://www.tenclass.com/)为小智生态制定了标准的通讯协议、多设备兼容性方案及高并发场景实践示范；为本项目提供了全链路技术文档支持 |
| <img src="./docs/images/logo_xuanfeng.png" width="160"> | [玄凤科技](https://github.com/Eric0308) | 感谢[玄凤科技](https://github.com/Eric0308)贡献函数调用框架、MCP通信协议及插件化调用机制的实现代码，通过标准化的指令调度体系与动态扩展能力，显著提升了前端设备(IoT)的交互效率和功能延展性 |
| <img src="./docs/images/logo_huiyuan.png" width="160"> | [汇远设计](http://ui.kwd988.net/) | 感谢[汇远设计](http://ui.kwd988.net/)为本项目提供专业视觉解决方案，用其服务超千家企业的设计实战经验，赋能本项目产品用户体验 |
| <img src="./docs/images/logo_qinren.png" width="160"> | [西安勤人信息科技](https://www.029app.com/) | 感谢[西安勤人信息科技](https://www.029app.com/)深化本项目视觉体系，确保整体设计风格在多场景应用中的一致性和扩展性 |


<a href="https://star-history.com/#xinnan-tech/xiaozhi-esp32-server&Date">

 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>