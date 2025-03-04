import json
from config.logger import setup_logging

logger = setup_logging()

async def handleVLMessage(conn, text):
    messages =  [
        {"type": "image_url","image_url": {"url": f"data:image/png;base64,{text}"},},
        {"type": "text", "text": "图中描绘的是什么景象,请细致查看并描述"},
    ]
    conn.executor.submit(conn.chat, messages)
