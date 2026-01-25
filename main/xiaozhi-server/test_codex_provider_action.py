from core.providers.llm.codex.codex import LLMProvider

cfg = {
    "type": "codex",
    "codex_bin": "codex.cmd",
    "effort": "medium",
    "log_stream": True, 
    "stream_debug": True, 
    "log_events":True,        # 把 thinking/action 事件写进同一个 log
    "event_max_chars": 0,   # 可选：事件 JSON 太长就截断；设 0 表示不截断
    "model_name": "gpt-5.2",
    "workspace": r"C:\Users\yibinjiang\Documents\GitHub\codex_app_server",
    "auto_approve": True,
    "network_access": True,
    "emit_events": True,
    "thinking_mode": "summary",   # 或 "raw"
    "show_actions": True,
    "summary": "detailed",        # 建议加，方便出 reasoning
}
p = LLMProvider(cfg)
dialogue = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "请列出当前目录文件名，并说明你做了哪些操作。然后回答 1+1=?"},
]

for chunk in p.response("probe", dialogue, emit_events=True):
    if isinstance(chunk, dict):
        print("[EVENT]", chunk)
    else:
        print(chunk, end="", flush=True)
print()