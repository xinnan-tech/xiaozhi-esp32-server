import json
from config.logger import setup_logging

logger = setup_logging()

async def handleVLMessage(conn, mesage):
    #print(text)
    messages =[]
    if conn.config["LLM"][conn.config["selected_module"]["LLM"]]['type']=='openai':
        print('当前openai接口协议LLM')
        messages = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{mesage['image']}"}, },
            {"type": "text", "text": "图中描绘的是什么景象,请细致查看并描述"+mesage['text']},
        ]
    conn.executor.submit(conn.chat, messages)
