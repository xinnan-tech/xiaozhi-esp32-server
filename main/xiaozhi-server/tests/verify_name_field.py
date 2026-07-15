"""实测:message 的 name 字段 vs JSON-content(傻方式)vs 无 speaker

验证用 OpenAI 原生 name 字段({role:user,name:xxx,content:yyy})能否替代
把 JSON 塞 content 的方式。如果 name 字段让 LLM 同样认出说话人、且 content 干净,
就可以替代那个"傻"设计。

用智谱 glm-4-flash(用户提供的 key)。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from openai import OpenAI

WANWAN = """[角色设定]
你是湾湾小何，来自中国台湾省的00后女生。讲话超级机车，喜欢用流行梗，
但会偷偷研究男友阿明的编程书籍。
[核心特征]
- 讲话像连珠炮，但会突然冒出超温柔语气
- 对科技话题有隐藏天赋
[交互指南]
讨论感情 → 炫耀程序员男友阿明但抱怨"他只会送键盘当礼物"
绝不：长篇大论，叽叽歪咽"""

with open("agent-base-prompt.txt", encoding="utf-8") as f:
    template = Template(f.read())
system_prompt = template.render(
    base_prompt=WANWAN,
    current_time="{{current_time}}",
    today_date="2026-07-12", today_weekday="星期日", lunar_date="六月十八",
    local_address="北京", weather_info="晴 32°C",
    emojiList="😊 😏 💅 🧋 📱 💻",
    device_id="test", client_ip="",
    dynamic_context="",
    language="中文",
)

client = OpenAI(
    api_key="f42a1a11b3bf40ee8524e74f7128c531.RosQvkwflutOSk4z",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

# 切换 name,都只问"我是谁",看 LLM 是否准确回 name 里那个人
cases = [
    ("① name=阿明",      [{"role": "user", "name": "阿明", "content": "你知道我是谁吗？"}]),
    ("② name=美琪",      [{"role": "user", "name": "美琪", "content": "你知道我是谁吗？"}]),
    ("③ name=张三(湾湾不认识)", [{"role": "user", "name": "张三", "content": "你知道我是谁吗？"}]),
    ("④ name=李四(湾湾不认识)", [{"role": "user", "name": "李四", "content": "你知道我是谁吗？"}]),
    ("⑤ 无 name(对照)",   [{"role": "user", "content": "你知道我是谁吗？"}]),
]

print("=" * 64)
print("切换 name + 问「你知道我是谁吗」:看 LLM 是否据 name 识别(glm-4-flash)")
print("=" * 64)
for label, msgs in cases:
    r = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "system", "content": system_prompt}] + msgs,
        max_tokens=80,
        temperature=0.5,
    )
    print(f"\n=== {label} ===")
    print(f"  user.name = {msgs[0].get('name', '(无)')}  content = {msgs[0]['content']}")
    print(f"  LLM 回复 → {r.choices[0].message.content}")
