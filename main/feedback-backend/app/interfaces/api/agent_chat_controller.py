"""后台 AI 数字人助手接口"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.agent_chat_service import AgentChatService
from app.infrastructure.persistence.database import SessionFactory, get_session
from app.infrastructure.persistence.models import AgentFeedbackCaseModel
from app.shared.config import settings
from app.shared.utils import generate_id
from app.interfaces.api.auth import (
    ROLE_STORE_MANAGER,
    _store_context,
    get_current_user,
    scoped_store_id,
)

router = APIRouter(prefix="/agent", tags=["AI助手"])


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    history: list[dict] | None = Field(default=None, description="最近对话上下文")


class AgentFeedbackRequest(BaseModel):
    message: str
    reply: str = ""
    intent: str = ""
    rating: str = Field(..., description="like/dislike")
    trace: list | dict | None = None
    notes: str = ""


@router.post("/chat")
async def chat(
    req: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """后台 AI 助手对话"""
    service = AgentChatService(session)
    result = await service.chat(
        message=req.message,
        history=req.history or [],
        store_id=scoped_store_id(current_user),
        operator=current_user.get("username", ""),
    )
    return {"code": 0, "msg": "success", "data": result}


async def _current_user_from_ws_token(token: str, session: Session) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.get("auth.secret_key"),
            algorithms=[settings.get("auth.algorithm", "HS256")],
        )
    except JWTError as exc:
        raise ValueError("无效的认证凭证") from exc

    username = payload.get("sub")
    if not username:
        raise ValueError("无效的认证凭证")
    role = payload.get("role") or "super_admin"
    ctx = {
        "username": username,
        "role": role,
        "store_id": payload.get("store_id"),
        "store_code": payload.get("store_code"),
        "store_name": payload.get("store_name"),
    }
    if role == ROLE_STORE_MANAGER and not ctx["store_id"]:
        ctx.update(_store_context(session, ctx.get("store_code") or username))
    return ctx


@router.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket):
    """后台 AI 助手长连接对话。

    管理后台数字人使用该通道保持一个持续会话；每条用户消息复用同一份
    conversation history，避免浏览器 ASR 一轮结束后显示 aborted。
    """
    token = websocket.query_params.get("token") or ""
    db = SessionFactory()
    try:
        current_user = await _current_user_from_ws_token(token, db)
    except ValueError as exc:
        await websocket.close(code=1008, reason=str(exc))
        db.close()
        return

    await websocket.accept()
    service = AgentChatService(db)
    history: list[dict] = []
    session_id = generate_id()
    await websocket.send_json({
        "type": "hello",
        "session_id": session_id,
        "text": "后台 AI 数字人长连接已建立",
    })

    try:
        while True:
            payload = await websocket.receive_json()
            msg_type = payload.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type == "reset":
                history.clear()
                await websocket.send_json({"type": "reset", "text": "上下文已清空"})
                continue
            if msg_type != "message":
                await websocket.send_json({"type": "error", "text": "不支持的消息类型"})
                continue

            text = str(payload.get("text") or "").strip()
            if not text:
                continue

            history.append({"role": "user", "text": text})
            await websocket.send_json({"type": "thinking", "text": "正在思考和查询..."})
            try:
                result = await service.chat(
                    message=text,
                    history=history[-12:],
                    store_id=scoped_store_id(current_user),
                    operator=current_user.get("username", ""),
                )
                reply = result.get("reply") or "已处理"
                history.append({"role": "assistant", "text": reply})
                await websocket.send_json({"type": "reply", "data": result, "text": reply})
            except Exception as exc:
                logger.exception(f"AI 长连接处理失败: {exc}")
                await websocket.send_json({"type": "error", "text": f"操作失败：{exc}"})
    except WebSocketDisconnect:
        logger.info(f"后台 AI 数字人长连接断开: session={session_id}, user={current_user.get('username')}")
    finally:
        db.close()


@router.post("/feedback")
async def feedback(
    req: AgentFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """记录 AI 助手点赞/点踩反馈。"""
    item = AgentFeedbackCaseModel(
        id=generate_id(),
        store_id=scoped_store_id(current_user),
        username=current_user.get("username"),
        message=req.message,
        reply=req.reply,
        intent=req.intent,
        rating=req.rating,
        trace=req.trace,
        notes=req.notes,
        status="open" if req.rating == "dislike" else "reviewed",
    )
    session.add(item)
    session.commit()
    return {"code": 0, "msg": "success", "data": {"id": item.id}}
