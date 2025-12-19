from fastapi import FastAPI, BackgroundTasks
import uvicorn
from pydantic import BaseModel
import time
import logging
from turn_det import analyze_text

# ---------------------
# 日志初始化
# ---------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------
# FastAPI 实例
# ---------------------
app = FastAPI(title="My HTTP Service")

# ---------------------
# 请求体
# ---------------------
class Item(BaseModel):
    text: str


# ---------------------
# 路由
# ---------------------

@app.get("/health")
def health():
    """健康检查接口"""
    return {
        "status": "ok",
        "timestamp": int(time.time())
    }


@app.get("/")
def root():
    return {"message": "Hello from FastAPI!"}


@app.post("/turn-detect")
def process(item: Item):
    """接收 JSON 请求并处理"""
    logger.info(f"Received: {item}")
    res = analyze_text(item.text)
    logger.info(f"result: {res}")
    result = {
        "text": item.text,
        "result":res
    }
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=18000)
