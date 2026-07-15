"""真实 agent 验证:用"湾湾小何"(从 manager-api DB 读到的人设)测 speaker 注入。

同一个 agent、同一个问题,带不同 speaker(男友/闺蜜)vs 不带,看 LLM 是否
真的据 speaker 切换语气/称呼 —— 验证本次改动在生产 agent 上的实际效果。

运行:python3 tests/verify_speaker_wanwan.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from openai import OpenAI

# 从 manager-api DB(ai_agent 表,id=a96fd5820fc04fe99e85c4ffafb34c98)读到的真实人设
WANWAN_PROMPT = """[角色设定]
你是湾湾小何，来自中国台湾省的00后女生。讲话超级机车，"真的假的啦"这样的台湾腔，喜欢用"笑死"、"哈噜"等流行梗，但会偷偷研究男友的编程书籍。
[核心特征]
- 讲话像连珠炮，但会突然冒出超温柔语气
- 用梗密度高
- 对科技话题有隐藏天赋（能看懂基础代码但假装不懂）
[交互指南]
当用户：
- 讲冷笑话 → 用夸张笑声回应+模仿台剧腔"这什么鬼啦！"
- 讨论感情 → 炫耀程序员男友但抱怨"他只会送键盘当礼物"
- 问专业知识 → 先用梗回答，被追问才展示真实理解
绝不：
- 长篇大论，叽叽歪咽
- 长时间严肃对话"""

# 真模板渲染(变量填示例值,保留 <speaker_recognition> 规则)
with open("agent-base-prompt.txt", encoding="utf-8") as f:
    template = Template(f.read())
system_prompt = template.render(
    base_prompt=WANWAN_PROMPT,
    current_time="{{current_time}}",
    today_date="2026-07-12",
    today_weekday="星期日",
    lunar_date="六月十八",
    local_address="北京",
    weather_info="晴 32°C",
    emojiList="😊 😏 💅 🧋 📱 💻 🎹",
    device_id="test-device",
    client_ip="",
    dynamic_context="",
    language="中文",
)

client = OpenAI(
    api_key="6202d63d-377b-4bd7-a2ad-c162ed977c24",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

cases = [
    ("① 带 speaker: 阿明(男友)",
     '{"speaker": "阿明(男友)", "content": "嘿,你那个程序员男友送的键盘好用吗?"}'),
    ("② 带 speaker: 美琪(闺蜜)",
     '{"speaker": "美琪(闺蜜)", "content": "你那个程序员男友最近怎么样啊?"}'),
    ("③ 不带 speaker(对照)",
     "你那个程序员男友最近怎么样啊?"),
    ("④ 带 speaker: 未知说话人",
     '{"speaker": "未知说话人", "content": "你认识我吗?"}'),
]

print("=" * 64)
print("agent = 湾湾小何(真实生产人设,来自 manager-api DB)")
print("=" * 64)
for label, user_content in cases:
    r = client.chat.completions.create(
        model="doubao-seed-2-0-lite-260428",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=120,
        temperature=0.8,
    )
    print(f"\n=== {label} ===")
    print(f"  user      → {user_content}")
    print(f"  assistant → {r.choices[0].message.content}")
