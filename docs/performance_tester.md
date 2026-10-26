# 语音识别、流式语音识别、大语言模型、非流式语音合成、流式语音合成、视觉模型的性能测试工具使用指南

0.先装依赖（在main/xiaozhi-server目录下执行）
```
cd main/xiaozhi-server
pip install -r requirements.txt
```
测试脚本要 import `yaml`、`aiohttp`、`tabulate`，少一个都起不来。`tabulate` 不在 requirements.txt 里，是 `edge-tts` 间接带进来的。

1.在main/xiaozhi-server目录下创建data目录
2.在data目录下创建.config.yaml文件
3.在data/.config.yaml中，写入你的语音识别、大语言模型、非流式语音合成、流式语音合成、视觉模型的参数
例如：
```
LLM:
  ChatGLMLLM:
    # 定义LLM API类型
    type: openai
    # glm-4-flash 是免费的，但是还是需要注册填写api_key的
    # 可在这里找到你的api key https://bigmodel.cn/usercenter/proj-mgmt/apikeys
    model_name: glm-4-flash
    url: https://open.bigmodel.cn/api/paas/v4/
    api_key: 你的chat-glm web key

TTS:
  EdgeTTS:
    # 定义TTS API类型
    type: edge
    voice: zh-CN-XiaoxiaoNeural

VLLM:

ASR:
  FunASR:
    type: fun_local
    model_dir: models/SenseVoiceSmall
    language: auto
```
4.在main/xiaozhi-server目录下运行performance_tester.py: 
```
python performance_tester.py
```

## 几点说明

- 脚本第一行提示的 `docs/performance_tester.md` 就是本文档，它在仓库根目录的 `docs/` 下；脚本本身在 `main/xiaozhi-server/` 目录里跑，两处不是一个目录。
- LLM、VLLM、非流式语音合成这几项会把 `config.yaml` 和 `data/.config.yaml` 两份配置合并起来再遍历，所以实际会测**所有配好 api_key 的供应器**，不只是你在 `.config.yaml` 里写的那一个；api_key 还是占位符的会被跳过。
- 语音识别这一项读配置的方式不一样：它自己扫 `data/` 目录下的 `*.config.yaml`，只取其中的 `ASR` 段，**不会**用 `config.yaml` 里的默认值。想测语音识别，就得把供应器写进 `data/.config.yaml`。
- 流式语音合成一次会跑这些供应器：

| 供应器 | 说明 |
|---|---|
| `AliyunStreamTTS` | 阿里云流式 TTS，无条件调用 |
| `HuoshanDoubleStreamTTS` | 火山引擎流式 TTS，无条件调用 |
| `PaddleSpeechTTS` | PaddleSpeech 流式 TTS，无条件调用 |
| `LinkeraiTTS` | 无条件调用，但 `config.yaml` 的 TTS 段里没有这个供应器，要测得自己在 `.config.yaml` 里补上 |
| `IndexStreamTTS` | IndexStream 流式 TTS，无条件调用 |
| `AliBLTTS` | 阿里百炼流式 TTS，只在 `.config.yaml` 里配了才测 |
| `XunFeiTTS` | 讯飞流式 TTS，只在 `.config.yaml` 里配了才测 |

标了「无条件调用」的这几个，配置里没有对应供应器时，那一项会报错后跳过，不影响其它项。
