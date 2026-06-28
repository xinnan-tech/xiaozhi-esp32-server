"""智能体配置管理控制器 - 后台管理用"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.agent_config_service import AgentConfigService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, require_super_admin

router = APIRouter(prefix="/agent-config", tags=["智能体配置"])


class CreateAgentConfigRequest(BaseModel):
    """创建智能体配置请求"""
    agent_name: str = Field(..., description="智能体名称")
    agent_id: Optional[str] = Field(None, description="对应 xiaozhi-server 智能体 ID")
    dialogue_rounds: int = Field(7, ge=1, le=20, description="对话轮次")
    questions: Optional[list] = Field(None, description="问题列表")
    prompts_config: Optional[dict] = Field(None, description="提示词配置")
    llm_config: Optional[dict] = Field(None, description="LLM 配置")
    review_config: Optional[dict] = Field(None, description="点评生成规则")


class UpdateAgentConfigRequest(BaseModel):
    """更新智能体配置请求"""
    agent_name: Optional[str] = Field(None)
    agent_id: Optional[str] = Field(None)
    dialogue_rounds: Optional[int] = Field(None, ge=1, le=20)
    questions: Optional[list] = Field(None)
    prompts_config: Optional[dict] = Field(None)
    llm_config: Optional[dict] = Field(None)
    review_config: Optional[dict] = Field(None)
    status: Optional[int] = Field(None)


@router.get("/list")
async def list_agent_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """分页查询智能体配置"""
    require_super_admin(current_user)
    service = AgentConfigService(session)
    result = await service.list_page(page, page_size)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "list": [
                {
                    "id": c.id,
                    "agentName": c.agent_name,
                    "agentId": c.agent_id,
                    "dialogueRounds": c.dialogue_rounds,
                    "questions": c.questions,
                    "promptsConfig": c.prompts_config,
                    "llmConfig": c.llm_config,
                    "reviewConfig": c.review_config,
                    "status": c.status,
                    "createDate": str(c.create_date) if c.create_date else None,
                }
                for c in result["list"]
            ],
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["page_size"],
        },
    }


@router.post("")
async def create_agent_config(
    req: CreateAgentConfigRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """创建智能体配置"""
    require_super_admin(current_user)
    service = AgentConfigService(session)
    config = await service.create_config(
        agent_name=req.agent_name,
        agent_id=req.agent_id,
        dialogue_rounds=req.dialogue_rounds,
        questions=req.questions,
        prompts_config=req.prompts_config,
        llm_config=req.llm_config,
        review_config=req.review_config,
    )
    return {"code": 0, "msg": "success", "data": {"id": config.id}}


@router.put("/{config_id}")
async def update_agent_config(
    config_id: str,
    req: UpdateAgentConfigRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """更新智能体配置"""
    require_super_admin(current_user)
    service = AgentConfigService(session)
    kwargs = req.model_dump(exclude_none=True)
    config = await service.update_config(config_id, **kwargs)
    return {"code": 0, "msg": "success", "data": {"id": config.id}}


@router.post("/delete")
async def delete_agent_config(
    config_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """删除智能体配置"""
    require_super_admin(current_user)
    service = AgentConfigService(session)
    await service.delete_config(config_id)
    return {"code": 0, "msg": "success"}
