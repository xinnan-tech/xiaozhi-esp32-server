"""实测:<current_speaker> 块(含姓名+与主人关系)

system 提示词里加 <current_speaker> 块(独立标签,不混进用户的话),切换不同说话人,
都问同一句,看 LLM 是否据块叫出名字 + 说出和主人的关系。

对比之前:name 字段(元数据)被 glm 忽略;此测试验证 in-content 的标签块是否可靠。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from openai import OpenAI

WANWAN = """[角色设定]
你是湾湾小何，来自中国台湾省的00后女生，居住在主人家里。讲话超级机车，喜欢用流行梗。
[核心特征]
- 讲话像连珠炮，但会突然冒出超温柔语气
- 对不同人用不同称呼和语气（对长辈尊敬、对平辈调皮、对主人亲昵）
绝不：长篇大论，叽叽歪咽"""

with open("agent-base-prompt.txt", encoding="utf-8") as f:
    template = Template(f.read())
system_base = template.render(
    base_prompt=WANWAN,
    current_time="{{current_time}}",
    today_date="2026-07-12", today_weekday="星期日", lunar_date="六月十八",
    local_address="北京", weather_info="晴 32°C",
    emojiList="😊 😏 💅 🧋 📱",
    device_id="test", client_ip="",
    dynamic_context="",
    language="中文",
)

client = OpenAI(
    api_key="f42a1a11b3bf40ee8524e74f7128c531.RosQvkwflutOSk4z",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

# current_speaker 块:姓名 + 和主人的关系。切换它,user 问句不变。
cases = [
    ("① 张三(主人的爸爸)",
     "<current_speaker>当前说话人：张三，是主人的爸爸</current_speaker>"),
    ("② 李四(主人的妈妈)",
     "<current_speaker>当前说话人：李四，是主人的妈妈</current_speaker>"),
    ("③ 美琪(主人的闺蜜)",
     "<current_speaker>当前说话人：美琪，是主人的闺蜜</current_speaker>"),
    ("④ 阿明(主人本人)",
     "<current_speaker>当前说话人：阿明，是主人本人</current_speaker>"),
    ("⑤ 无 current_speaker(对照)",
     ""),
]

QUESTION = "你知道我是谁吗？我和主人是什么关系？"

print("=" * 64)
print("<current_speaker> 块(姓名+关系)glm-4-flash")
print("=" * 64)
for label, block in cases:
    system = system_base + (f"\n\n{block}" if block else "")
    r = client.chat.completions.create(
        model="glm-4-flash",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": QUESTION},
        ],
        max_tokens=100,
        temperature=0.5,
    )
    print(f"\n=== {label} ===")
    print(f"  block  = {block or '(无)'}")
    print(f"  user   = {QUESTION}")
    print(f"  reply  → {r.choices[0].message.content}")
