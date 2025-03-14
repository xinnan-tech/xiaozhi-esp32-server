from config.logger import setup_logging
import openai
from core.providers.llm.base import LLMProviderBase
from typing import Dict, Any
import json
from openai.types.chat.chat_completion import Choice

TAG = __name__
logger = setup_logging()

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if 'base_url' in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        if "你" in self.api_key:
            logger.bind(tag=TAG).error("你还没配置LLM的密钥，请在配置文件中配置密钥，否则无法正常工作")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def search_impl(self, arguments: Dict[str, Any]) -> Any:
        """
        在使用 Moonshot AI 提供的 search 工具的场合，只需要原封不动返回 arguments 即可，
        不需要额外的处理逻辑。

        但如果你想使用其他模型，并保留联网搜索的功能，那你只需要修改这里的实现（例如调用搜索
        和获取网页内容等），函数签名不变，依然是 work 的。

        这最大程度保证了兼容性，允许你在不同的模型间切换，并且不需要对代码有破坏性的修改。
        """
        return arguments

    def chat(self, messages) -> Choice:
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.3,
            tools=[
                {
                    "type": "builtin_function",
                    "function": {
                        "name": "$web_search",
                    },
                }
            ]
        )
        return completion.choices[0]

    def response(self, session_id, dialogue):
        try:
            finish_reason = None
            while finish_reason is None or finish_reason == "tool_calls":
                choice = self.chat(dialogue)
                finish_reason = choice.finish_reason
                print(finish_reason)
                if finish_reason == "tool_calls":  # <-- 判断当前返回内容是否包含 tool_calls
                    dialogue.append(choice.message)  # <-- 我们将 Kimi 大模型返回给我们的 assistant 消息也添加到上下文中，以便于下次请求时 Kimi 大模型能理解我们的诉求
                    for tool_call in choice.message.tool_calls:  # <-- tool_calls 可能是多个，因此我们使用循环逐个执行
                        tool_call_name = tool_call.function.name
                        tool_call_arguments = json.loads(tool_call.function.arguments)  # <-- arguments 是序列化后的 JSON Object，我们需要使用 json.loads 反序列化一下
                        if tool_call_name == "$web_search":
                            tool_result = self.search_impl(tool_call_arguments)
                        else:
                            tool_result = f"Error: unable to find tool by name '{tool_call_name}'"

                        # 使用函数执行结果构造一个 role=tool 的 message，以此来向模型展示工具调用的结果；
                        # 注意，我们需要在 message 中提供 tool_call_id 和 name 字段，以便 Kimi 大模型
                        # 能正确匹配到对应的 tool_call。
                        dialogue.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call_name,
                            "content": json.dumps(tool_result),  # <-- 我们约定使用字符串格式向 Kimi 大模型提交工具调用结果，因此在这里使用 json.dumps 将执行结果序列化成字符串
                        })

            return choice.message.content

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in response generation: {e}")
