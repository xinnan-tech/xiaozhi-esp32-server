"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pathlib import Path

from app.infrastructure.persistence.database import SessionFactory, init_database
from app.infrastructure.persistence.models import AdminUserModel
from app.interfaces.api.auth import init_default_admin
from app.interfaces.api.router import api_router
from app.shared.config import settings
from app.shared.exceptions import FeedbackBaseException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化"""
    logger.info("Feedback Backend starting...")

    # 初始化数据库表（开发模式；生产环境应使用 Alembic 迁移）
    try:
        init_database()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning(f"Database init failed (check DB connection): {e}")

    # 初始化默认管理员
    try:
        session = SessionFactory()
        init_default_admin(session)
        session.close()
    except Exception as e:
        logger.warning(f"Admin init failed: {e}")

    logger.info(f"Feedback Backend ready - http://{settings.get('server.host', '0.0.0.0')}:{settings.get('server.port', 8009)}")

    yield

    logger.info("Feedback Backend shutdown")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="反馈系统后端",
        description="客户反馈系统独立后端服务 - DDD 架构",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 中间件
    cors_origins = settings.get("server.cors_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 信任代理头（Nginx 反向代理时需要）
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    trusted_hosts = settings.get("server.trusted_hosts", [])
    if trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=trusted_hosts,
        )

    # 全局异常处理
    @app.exception_handler(FeedbackBaseException)
    async def feedback_exception_handler(request: Request, exc: FeedbackBaseException):
        return JSONResponse(
            status_code=400,
            content={"code": exc.code, "msg": exc.message, "data": None},
        )

    # 注册 API 路由
    app.include_router(api_router)

    # 挂载 admin-ui 静态文件（如果存在）
    admin_ui_dir = Path(__file__).resolve().parent.parent / "admin-ui"
    if admin_ui_dir.exists():
        app.mount("/admin", StaticFiles(directory=str(admin_ui_dir), html=True), name="admin-ui")

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "feedback-backend"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.get("server.host", "0.0.0.0"),
        port=settings.get("server.port", 8009),
        reload=settings.get("server.debug", True),
    )
