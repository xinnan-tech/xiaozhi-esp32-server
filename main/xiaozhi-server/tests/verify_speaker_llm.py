"""真实验证:speaker 注入是否让 LLM 知道是谁。

用真的 agent-base-prompt.txt 模板(含 <speaker_recognition> 规则)+ 真 doubao LLM,
对照实验:同一个问题,带 vs 不带 speaker,看 LLM 回复差异。

这验证的是 enhanced_text JSON({"speaker":...,"content":...})经模板 <speaker_recognition>
规则,LLM 是否真的识别出说话人 —— 即本次改动最终要达到的效果。

运行:python3 tests/verify_speaker_llm.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Template
from openai import OpenAI

# 读真模板并渲染(变量填示例值,保留 <speaker_recognition> 规则原文)
with open("agent-base-prompt.txt", encoding="utf-8") as f:
    template = Template(f.read())
system_prompt = template.render(
    base_prompt="你是小智,一个温暖幽默的家庭语音助手,服务于张三一家"
    "(爸爸张三、妈妈李四、儿子张小宝)。",
    current_time="{{current_time}}",
    today_date="2026-07-12",
    today_weekday="星期日",
    lunar_date="六月十八",
    local_address="北京",
    weather_info="晴 32°C",
    emojiList="😊 🤗 🎵 🎬 ☀️ 💡 🦊 🌙 🎸 👋",
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
    ("① 带 speaker: 张三(爸爸)",
     '{"speaker": "张三(爸爸)", "content": "你认识我吗?我是谁?"}'),
    ("② 不带 speaker(对照)",
     "你认识我吗?我是谁?"),
    ("③ speaker=未知说话人",
     '{"speaker": "未知说话人", "content": "你认识我吗?我是谁?"}'),
    ("④ 带 speaker: 李四(妈妈)",
     '{"speaker": "李四(妈妈)", "content": "我是谁?"}'),
]

print("=" * 60)
print("system prompt 含 <speaker_recognition> 规则(取自 agent-base-prompt.txt)")
print("=" * 60)
for label, user_content in cases:
    r = client.chat.completions.create(
        model="doubao-seed-2-0-lite-260428",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=80,
        temperature=0.7,
    )
    print(f"\n=== {label} ===")
    print(f"  user      → {user_content}")
    print(f"  assistant → {r.choices[0].message.content}")
