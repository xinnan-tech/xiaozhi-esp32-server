"""启动脚本 - 方便快速启动服务"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.shared.config import settings


def main():
    host = settings.get("server.host", "0.0.0.0")
    port = settings.get("server.port", 8009)
    debug = settings.get("server.debug", True)

    print(f"Feedback Backend starting...")
    print(f"  URL:    http://{host}:{port}")
    print(f"  Docs:   http://{host}:{port}/docs")
    print(f"  Admin:  http://{host}:{port}/admin")
    print(f"  Debug:  {'ON' if debug else 'OFF'}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
