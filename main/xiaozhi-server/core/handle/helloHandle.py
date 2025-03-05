import json
from config.logger import setup_logging

logger = setup_logging()


async def handleHelloMessage(conn):
    await conn.websocket.send(json.dumps(conn.welcome_msg))
