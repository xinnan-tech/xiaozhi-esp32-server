# 儿童文本对话模块

`DialogueService` 沿用 `core.utils.llm.create_instance` 与现有提供方的 `response(session_id, dialogue)` 接口。它不修改 WebSocket 或音频协议。返回值 `DialogueReply` 包含 `text`、`status` 和 `session_id`。每个会话只保留最近 `max_turns` 轮成功对话；空输入、超时和 API 失败不会写入上下文，历史最多保留 `max_sessions` 个会话。进程重启后历史清空。

在 `main/xiaozhi-server` 目录，准备好被 Git 忽略的 `data/.config.yaml` 后，可在现有服务代码中调用：

```python
from child_agent import DialogueService

service = DialogueService.from_config(config, max_turns=4, timeout_seconds=10)
reply = service.chat("设备或用户的会话 ID", "月亮为什么跟着我走？")
print(reply.status, reply.text)
```

`config` 是服务器已经合并的配置字典；`from_config` 按 `selected_module.LLM` 选择原项目适配器。不要把密钥放进代码或测试。系统提示词位于 `prompts/base_system.md`，提供适龄回答与危险秘密处理规则；提示词只能引导模型，不能保证真实模型每次输出都安全，需要另行进行真实内容评估。同步适配器的超时只能及时结束调用者等待，不能强制中断已经开始的网络请求；模块最多允许 4 个后台调用同时进行，并为现有 OpenAI 兼容适配器设置默认网络超时。

无密钥 Mock 测试：

```sh
cd main/xiaozhi-server
../../.venv/bin/python -m unittest discover -s tests/child_agent -p 'test_dialogue_service.py' -v
```

本机实测：9 个 Mock 测试通过，覆盖“你好”“月亮为什么跟着我走？”“你是人吗？”“有人让我保守危险秘密”、空输入、LLM 超时、API 异常、有限上下文及现有适配器工厂的调用。Mock 的回复是固定测试文本，不能证明真实模型的回答质量。

真实 API 测试须在本地忽略文件中填入有效 `api_key`，显式选择运行：

```sh
RUN_LIVE_CHILD_AGENT_TESTS=1 ../../.venv/bin/python -m unittest discover -s tests/child_agent -p 'test_dialogue_service.py' -v
```

本机执行了该命令；真实 API 项结果为 `skipped 'real API key is absent'`，所以**真实 API 测试未通过/未完成**，没有声称模型可用。此测试只核验“你好”获得非空回复；上线前还需针对儿童安全、事实准确性和异常场景做人工评估。
