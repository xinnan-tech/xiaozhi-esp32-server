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
如需提升响应速度，可尝试更换各组件。以下为各组件的响应速度测试数据（仅供参考，不构成承诺）：

| 影响因素  |       因素值        | 
|:-----:|:----------------:|
| 测试地点  |    广东省广州市海珠区     |
| 测试时间  | 2025年2月19日 12:52 |
| 宽带运营商 |       中国联通       |

测试方法：

1、把各组件的密钥配置上去，只有配置了密钥的组件才参与测试。

2、配置完密钥后，执行以下方法

```
# 进入项目根目录，执行以下命令：
conda activate xiaozhi-esp32-server
python performance_tester.py 
```

生成报告如下

LLM 性能排行:

| 模块名称       | 平均首Token时间 | 平均总响应时间 |
|:-----------|:-----------|:--------|
| AliLLM     | 0.547s     | 1.485s  |
| ChatGLMLLM | 0.677s     | 3.057s  |

TTS 性能排行:

| 模块名称                 | 平均合成时间 |
|----------------------|--------|
| EdgeTTS              | 1.019s |
| DoubaoTTS            | 0.503s |
| CosyVoiceSiliconflow | 3.732s |

推荐配置组合 (综合响应速度):

| 组合方案                          | 综合得分  | LLM首Token | TTS合成  |
|-------------------------------|-------|-----------|--------|
| AliLLM + DoubaoTTS            | 0.539 | 0.547s    | 0.503s |
| AliLLM + EdgeTTS              | 0.642 | 0.547s    | 1.019s |
| ChatGLMLLM + DoubaoTTS        | 0.642 | 0.677s    | 0.503s |
| ChatGLMLLM + EdgeTTS          | 0.745 | 0.677s    | 1.019s |
| AliLLM + CosyVoiceSiliconflow | 1.184 | 0.547s    | 3.732s |

### 结论 🔍

`2025年2月19日`，如果我的电脑在`广东省广州市海珠区`，且使用的是`中国联通`网络，我会优先使用：

- LLM：`AliLLM`
- TTS：`DoubaoTTS`

### 6、我说话很慢，停顿时小智老是抢话 🗣️

建议：在配置文件中找到如下部分，将 `min_silence_duration_ms` 的值调大（例如改为 `1000`）：

```yaml
VAD:
  SileroVAD:
    threshold: 0.5
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 700  # 如果说话停顿较长，可将此值调大
```

### 7、我想通过小智控制电灯、空调、远程开关机等操作 💡

参考教程[ESP32设备与HomeAssistant集成指南](./homeassistant-integration.md)

### 8、更多问题，可联系我们反馈 💬

可以在[issues](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues)提交您的问题。

也可以发邮件我们取得联系：huangrongzhuang@xin-nan.com