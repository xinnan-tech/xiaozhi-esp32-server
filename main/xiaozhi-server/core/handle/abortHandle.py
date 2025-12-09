import json

from config.logger import setup_logging
TAG = __name__
logger = setup_logging()

async def handleAbortMessage(conn):
    logger.bind(tag=TAG).info(f"客户端{conn.client_listen_mode}模式下，收到打断消息")
    # 设置成打断状态，会自动打断llm、tts任务
    conn.client_abort = True
    conn.clear_queues()
    # 打断客户端说话状态
    await conn.websocket.send(
        json.dumps({"type": "tts", "state": "stop", "session_id": conn.session_id})
    )
    conn.clearSpeakStatus()
    conn.logger.bind(tag=TAG).info("Abort message received-end")
