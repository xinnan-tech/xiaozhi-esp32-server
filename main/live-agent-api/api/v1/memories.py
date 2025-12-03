from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from api.auth import get_current_user_id
from services.memory_service import memory_service
from utils.response import success_response
from schemas.memory import (
    MemorySearchRequest,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryDeleteRequest,
    MemorySharingGetRequest,
    MemorySharingUpdateRequest,
)

router = APIRouter()


# ==================== Memory CRUD ====================

@router.post("/search", summary="Search memories")
async def search_memories(
    request: MemorySearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索记忆（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
        - query: 搜索关键词（可选）
        - type: 记忆类型筛选 profile | event（可选）
        - cursor: 分页游标（可选）
        - limit: 每页数量（默认 20）
        - include_shared: 是否包含共享记忆（默认 true）
    """
    result = await memory_service.search_memories(
        db=db,
        user_id=user_id,
        agent_id=request.agent_id,
        query=request.query,
        memory_type=request.type,
        cursor=request.cursor,
        limit=request.limit,
        include_shared=request.include_shared
    )
    return success_response(data=result.model_dump())


@router.post("/create", summary="Create memory")
async def create_memory(
    request: MemoryCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    创建记忆（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
        - type: 记忆类型 profile | event
        - content: 记忆内容
        - title: 标题（event 类型需要）
    """
    result = await memory_service.create_memory(
        user_id=user_id,
        agent_id=request.agent_id,
        memory_type=request.type,
        content=request.content,
        title=request.title
    )
    return success_response(data=result.model_dump())


@router.put("/update", summary="Update memory")
async def update_memory(
    request: MemoryUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新记忆（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
        - memory_id: 记忆 ID
        - title: 新标题（可选）
        - content: 新内容（可选）
    """
    result = await memory_service.update_memory(
        user_id=user_id,
        agent_id=request.agent_id,
        memory_id=request.memory_id,
        title=request.title,
        content=request.content
    )
    return success_response(data=result.model_dump())


@router.delete("/delete", summary="Delete memory")
async def delete_memory(
    request: MemoryDeleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    删除记忆（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
        - memory_id: 记忆 ID
    """
    await memory_service.delete_memory(
        user_id=user_id,
        agent_id=request.agent_id,
        memory_id=request.memory_id
    )
    return success_response(data={"success": True})


# ==================== Memory Sharing Config ====================

@router.post("/sharing/get", summary="Get sharing config")
async def get_memory_sharing(
    request: MemorySharingGetRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取记忆共享配置（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
    
    Returns:
        - share_type: none | specific | all
        - shared_with: 共享目标 Agent ID 列表
    """
    result = await memory_service.get_memory_sharing(
        db=db,
        user_id=user_id,
        agent_id=request.agent_id
    )
    return success_response(data=result.model_dump())


@router.put("/sharing/update", summary="Update sharing config")
async def update_memory_sharing(
    request: MemorySharingUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新记忆共享配置（需要 Bearer Token 认证）
    
    Request Body:
        - agent_id: Agent ID
        - share_type: none | specific | all
        - shared_with: 共享目标 Agent ID 列表（share_type=specific 时需要）
    
    Share types:
        - none: 不共享
        - specific: 共享给指定 agents
        - all: 共享给所有 agents
    """
    result = await memory_service.update_memory_sharing(
        db=db,
        user_id=user_id,
        agent_id=request.agent_id,
        share_type=request.share_type,
        shared_with=request.shared_with
    )
    return success_response(data=result.model_dump())
