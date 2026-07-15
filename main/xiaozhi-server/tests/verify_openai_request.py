"""直接打印发给 OpenAI 接口的 messages(JSON payload 的 content),并真发到 LLM。

dialogue.get_llm_dialogue_with_memory 返回的就是 OpenAI messages 格式。
json.dumps 它就是 POST /chat/completions body 里的 messages。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from openai import OpenAI
from core.utils.dialogue import Dialogue, Message

system_prompt = Template(open("agent-base-prompt.txt", encoding="utf-8").read()).render(
    base_prompt=(
        "[角色设定]\n你是湾湾小何，台湾00后女生，住在主人家。机车爱用梗，"
        "对不同人用不同称呼（长辈尊敬、平辈调皮、主人亲昵）。"
    ),
    current_time="{{current_time}}",
    today_date="2026-07-12", today_weekday="星期日", lunar_date="六月十八",
    local_address="北京", weather_info="晴 32°C",
    emojiList="😊 😏 💅 🧋", device_id="test", client_ip="",
    dynamic_context="", language="中文",
)

d = Dialogue()
d.put(Message(role="system", content=system_prompt))
d.put(Message(role="user", content="你男友最近咋样？"))
d.put(Message(role="assistant", content="他啊，整天敲代码~"))
d.put(Message(role="user", content="你好"))  # 当前轮用户输入(B 方案:纯文本)

# 这就是发给 OpenAI 接口的 messages
msgs = d.get_llm_dialogue_with_memory(
    memory_str="- 主人最近在学吉他\n- 张小宝怕黑",
    voiceprint_config={"speakers": ["张三,爸爸,喜欢摇滚", "李四,妈妈,在减肥"]},
    current_speaker={"name": "张三", "relationship": "爸爸"},
)

print("=" * 72)
print("POST /chat/completions  body.messages (发给 OpenAI 接口的 content):")
print("=" * 72)
print(json.dumps(msgs, ensure_ascii=False, indent=2))

# 真发到智谱 LLM
print("\n" + "=" * 72)
print("真发到 glm-4-flash,看回复(验证 B 方案:认出张三爸爸):")
print("=" * 72)
client = OpenAI(
    api_key="f42a1a11b3bf40ee8524e74f7128c531.RosQvkwflutOSk4z",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
r = client.chat.completions.create(
    model="glm-4-flash", messages=msgs, max_tokens=120, temperature=0.6,
)
print(r.choices[0].message.content)
