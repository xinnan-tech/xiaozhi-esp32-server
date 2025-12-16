from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ==================== 基础请求（agent_id，user_id 从 token 获取）====================

class MemoryBaseRequest(BaseModel):
    """所有 Memory 请求的基类（user_id 从 JWT token 获取）"""
    agent_id: str = Field(..., description="Agent ID")


# ==================== Memory CRUD 请求 ====================

class MemorySearchRequest(MemoryBaseRequest):
    """搜索记忆请求"""
    query: Optional[str] = Field(None, description="搜索关键词")
    type: Optional[Literal["profile", "event"]] = Field(None, description="记忆类型筛选")
    cursor: Optional[str] = Field(None, description="分页游标")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    include_shared: bool = Field(True, description="是否包含共享记忆")


class MemoryCreateRequest(MemoryBaseRequest):
    """创建记忆请求"""
    type: Literal["profile", "event"] = Field(..., description="记忆类型")
    content: str = Field(..., description="记忆内容")
    title: Optional[str] = Field(None, description="标题（event 类型需要）")


class MemoryUpdateRequest(MemoryBaseRequest):
    """更新记忆请求"""
    memory_id: str = Field(..., description="记忆 ID")
    title: Optional[str] = Field(None, description="新标题")
    content: Optional[str] = Field(None, description="新内容")


class MemoryDeleteRequest(MemoryBaseRequest):
    """删除记忆请求"""
    memory_id: str = Field(..., description="记忆 ID")


# ==================== Memory Sharing 请求 ====================

class MemorySharingGetRequest(MemoryBaseRequest):
    """获取共享配置请求"""
    pass


class MemorySharingUpdateRequest(MemoryBaseRequest):
    """更新共享配置请求"""
    share_type: Literal["none", "specific", "all"] = Field(..., description="共享类型")
    shared_with: Optional[List[str]] = Field(
        None, 
        description="共享目标 Agent ID 列表（share_type=specific 时需要）"
    )


# ==================== 响应 ====================

class MemoryResponse(BaseModel):
    """记忆响应"""
    id: str = Field(..., description="记忆 ID")
    agent_id: str = Field(..., description="记忆所属的 Agent ID")
    type: str = Field(..., description="记忆类型（透传 MemU 返回的 category）")
    title: Optional[str] = Field(None, description="标题")
    content: str = Field(..., description="记忆内容")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_shared: bool = Field(False, description="是否为共享记忆")
    shared_from: Optional[str] = Field(None, description="共享来源 Agent ID")

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    memories: List[MemoryResponse] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(None, description="下一页游标")
    has_more: bool = Field(False, description="是否有更多")


class MemorySharingConfig(BaseModel):
    """共享配置响应"""
    share_type: Literal["none", "specific", "all"] = Field(..., description="共享类型")
    shared_with: Optional[List[str]] = Field(None, description="共享目标 Agent ID 列表")


class MemoryDeleteResponse(BaseModel):
    """删除响应"""
    success: bool = Field(True, description="是否成功")
