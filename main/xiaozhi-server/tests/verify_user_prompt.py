"""完整实例:LLM 收到的全部消息(真模板渲染 + 多轮 + current_speaker)

打印发给 LLM 的每一条 message(role + 完整 content),看 B 方案下:
- system(模板渲染,含 <speaker_recognition>)
- 实时 user 段(<current_speaker> 块 + <memory> + <speakers_info>)
- 对话历史(用户实际输入,纯文本)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from core.utils.dialogue import Dialogue, Message

# 真 agent-base-prompt.txt + 湾湾小何人设
with open("agent-base-prompt.txt", encoding="utf-8") as f:
    system_prompt = Template(f.read()).render(
        base_prompt=(
            "[角色设定]\n你是湾湾小何，来自中国台湾省的00后女生，住在主人家。"
            "讲话超级机车，喜欢用流行梗，但会偷偷研究主人男友阿明的编程书籍。"
        ),
        current_time="{{current_time}}",
        today_date="2026-07-12", today_weekday="星期日", lunar_date="六月十八",
        local_address="北京", weather_info="晴，32°C",
        emojiList="😊 😏 💅 🧋 📱 💻",
        device_id="30:ed:a0:1e:8f:24", client_ip="",
        dynamic_context="",
        language="中文",
    )

d = Dialogue()
d.put(Message(role="system", content=system_prompt))
# 历史一轮
d.put(Message(role="user", content="你男友最近咋样？"))
d.put(Message(role="assistant", content="他啊，整天敲代码，键盘当礼物我也是醉了~"))
# 当前轮:张三(主人爸爸)说"你好" —— B 方案,content 纯文本
d.put(Message(role="user", content="你好"))

msgs = d.get_llm_dialogue_with_memory(
    memory_str="- 主人最近在学吉他\n- 张小宝怕黑",
    voiceprint_config={"speakers": [
        "张三,爸爸,喜欢摇滚",
        "李四,妈妈,在减肥",
        "张小宝,儿子,6岁",
    ]},
    current_speaker={"name": "张三", "relationship": "爸爸"},
)

for i, m in enumerate(msgs):
    print("=" * 72)
    print(f"【消息 {i}】 role = {m['role']}")
    print("=" * 72)
    print(m["content"])
    print()
