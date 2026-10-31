"""S2S（speech-to-speech，语音进、语音出）provider 插槽。

原版链路是 VAD → ASR → 文字 LLM → TTS 的级联，一问一答。S2S provider 把中间那一格换成一个自己判轮次、自己出声、
能被打断的实时语音模型（OpenAI Realtime、GPT-Live 等），设备侧协议完全不变：

    设备 Opus → connection._route_message 解成 PCM → provider.on_pcm → 上游模型
    上游音频 → provider → 60 ms Opus → 上游现成的 sendAudio 节拍器 → 设备
    工具       → conn.func_handler（服务端插件 / server_mcp / 设备 MCP / MCP 接入点）
    打断       → 设备 abort / 模型侧 VAD / 本地门控 → handleAbortMessage + provider.cancel
    记忆       → 转写写进 conn.dialogue，关闭时由原版保存

选中方式：selected_module.S2S 指向 S2S 配置块里的一个 provider；握手失败自动回退到原版级联（同一连接，设备无感）。
目录约定与 LLM / TTS 一样：core/providers/s2s/<type>/<type>.py 里的 S2SProvider 类，由 core/utils/s2s.py 创建。
"""
