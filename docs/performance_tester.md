# 语音识别、流式语音识别、大语言模型、非流式语音合成、流式语音合成、视觉模型的性能测试工具使用指南

1.在main/xiaozhi-server目录下创建data目录
2.在data目录下创建.config.yaml文件
3.在.data/config.yaml中，写入你的语音识别、大语言模型、流式语音合成、视觉模型的参数
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

VLLM:

ASR:
```
4.在main/xiaozhi-server目录下运行performance_tester.py: 
```
python performance_tester.py
```