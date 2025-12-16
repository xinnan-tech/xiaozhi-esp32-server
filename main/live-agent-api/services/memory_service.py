from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import uuid
from datetime import datetime

from config import settings
from utils.exceptions import NotFoundException, BadRequestException
from schemas.memory import (
    MemoryResponse,
    MemoryListResponse,
    MemorySharingConfig,
)
from repositories.memory_sharing import MemorySharingRepository


class MemoryService:
    """Memory service - 调用下游 MemU API + 本地共享逻辑"""

    # Mock 数据存储（内存中，重启后清空）
    _mock_memories: dict = {}

    def __init__(self):
        self.base_url = settings.MEMU_BASE_URL if hasattr(settings, 'MEMU_BASE_URL') else "https://api.memu.so"
        self.api_key = settings.MEMU_API_KEY if hasattr(settings, 'MEMU_API_KEY') else ""
        # 当 MemU 不可用时自动 fallback 到 mock 模式
        self.use_mock = True

    @property
    def _headers(self) -> dict:
        """构造请求头（MEMu API v2 使用 Bearer Token）"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """统一的 HTTP 请求方法（调用 MemU 下游 API）"""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload,
                params=params,
                headers=self._headers
            )
            if response.status_code == 404:
                raise NotFoundException("Resource not found")
            response.raise_for_status()
            return response.json()

    # ==================== Mock 数据方法 ====================

    def _mock_key(self, user_id: str, agent_id: str) -> str:
        """生成 mock 存储的 key"""
        return f"{user_id}:{agent_id}"

    def _mock_create(self, user_id: str, agent_id: str, memory_type: str, summary: str) -> dict:
        """Mock: 创建记忆"""
        now = datetime.utcnow().isoformat() + "Z"
        memory_id = str(uuid.uuid4())
        item = {
            "id": memory_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "memory_type": memory_type,
            "summary": summary,
            "created_at": now,
            "updated_at": now
        }
        key = self._mock_key(user_id, agent_id)
        if key not in self._mock_memories:
            self._mock_memories[key] = {}
        self._mock_memories[key][memory_id] = item
        return item

    def _mock_update(self, user_id: str, agent_id: str, memory_id: str, summary: str) -> dict:
        """Mock: 更新记忆"""
        key = self._mock_key(user_id, agent_id)
        if key in self._mock_memories and memory_id in self._mock_memories[key]:
            self._mock_memories[key][memory_id]["summary"] = summary
            self._mock_memories[key][memory_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            return self._mock_memories[key][memory_id]
        raise NotFoundException("Memory not found")

    def _mock_delete(self, user_id: str, agent_id: str, memory_id: str) -> dict:
        """Mock: 删除记忆"""
        key = self._mock_key(user_id, agent_id)
        if key in self._mock_memories and memory_id in self._mock_memories[key]:
            del self._mock_memories[key][memory_id]
            return {"success": True}
        raise NotFoundException("Memory not found")

    def _mock_search(self, user_id: str, agent_ids: List[str], query: Optional[str] = None) -> dict:
        """Mock: 搜索记忆（query 为空时返回全量）"""
        items = []
        for agent_id in agent_ids:
            key = self._mock_key(user_id, agent_id)
            if key in self._mock_memories:
                for item in self._mock_memories[key].values():
                    # query 为空返回全部，否则按关键词过滤
                    if not query or query.lower() in item.get("summary", "").lower():
                        items.append(item)
        return {"memory_items": items}

    # ==================== 下游 MemU API 调用（带 Mock Fallback）====================

    async def _memu_create(self, user_id: str, agent_id: str, memory_type: str, summary: str) -> dict:
        """POST /memory-items（失败时 fallback 到 mock）"""
        try:
            payload = {
                "user_id": user_id,
                "agent_id": agent_id,
                "memory_type": memory_type,
                "summary": summary
            }
            return await self._request("POST", "/memory-items", payload=payload)
        except Exception:
            if self.use_mock:
                return self._mock_create(user_id, agent_id, memory_type, summary)
            raise

    async def _memu_update(self, user_id: str, agent_id: str, memory_item_id: str, summary: str) -> dict:
        """PUT /memory-items/{memory-item-id}（失败时 fallback 到 mock）"""
        try:
            payload = {
                "user_id": user_id,
                "agent_id": agent_id,
                "summary": summary
            }
            return await self._request("PUT", f"/memory-items/{memory_item_id}", payload=payload)
        except Exception:
            if self.use_mock:
                return self._mock_update(user_id, agent_id, memory_item_id, summary)
            raise

    async def _memu_delete(self, user_id: str, agent_id: str, memory_item_id: str) -> dict:
        """DELETE /memory-items/{memory-item-id}（失败时 fallback 到 mock）"""
        try:
            params = {"user_id": user_id, "agent_id": agent_id}
            return await self._request("DELETE", f"/memory-items/{memory_item_id}", params=params)
        except Exception:
            if self.use_mock:
                return self._mock_delete(user_id, agent_id, memory_item_id)
            raise

    async def _memu_search(self, user_id: str, agent_ids: List[str], query: Optional[str] = None) -> dict:
        """调用 MEMu API v2 查询记忆（失败时 fallback 到 mock）
        
        统一使用 /api/v2/memory/retrieve/related-memory-items 搜索接口
        - 有 query 时：使用具体关键词搜索
        - 无 query 时：使用通用 query 获取全量记忆
        
        注意：MEMu API 每次只支持单个 agent_id，需要对多个 agent 分别查询后合并
        """
        all_items = []
        
        # 无 query 时使用通用搜索词获取全量记忆
        search_query = query if query else "记忆 用户 事件 偏好"
        
        for agent_id in agent_ids:
            try:
                payload = {
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "query": search_query,
                    "top_k": 100,  # 获取更多结果
                    "min_similarity": 0.1 if not query else 0.3  # 无 query 时降低相似度阈值
                }
                data = await self._request("POST", "/api/v2/memory/retrieve/related-memory-items", payload=payload)
                
                # 提取 related_memories 列表，解析嵌套的 memory 对象
                # 直接透传返回的 category，不做过滤
                related_memories = data.get("related_memories", [])
                for rm in related_memories:
                    memory = rm.get("memory", {})
                    if memory:
                        category = memory.get("category", "").lower()
                        # 标准化字段名
                        item = {
                            "id": memory.get("memory_id", ""),
                            "agent_id": agent_id,
                            "user_id": user_id,
                            "memory_type": category,
                            "summary": memory.get("content", ""),
                            "created_at": memory.get("created_at", ""),
                            "updated_at": memory.get("updated_at", ""),
                        }
                        all_items.append(item)
            except Exception as e:
                # 单个 agent 查询失败，继续处理其他 agent
                import logging
                logging.warning(f"MEMu query failed for agent {agent_id}: {e}")
                continue
        
        # 如果所有 agent 都失败，尝试 mock fallback
        if not all_items and self.use_mock:
            return self._mock_search(user_id, agent_ids, query)
        
        return {"memory_items": all_items}

    # ==================== 对外 API：Memory CRUD ====================

    async def search_memories(
        self,
        db: AsyncSession,
        user_id: str,
        agent_id: str,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
        include_shared: bool = True
    ) -> MemoryListResponse:
        """搜索记忆
        
        1. 从 DB 查询共享给该 agent 的源 agent 列表
        2. 合并自己的 agent_id，构建查询列表
        3. 一次性调用 MemU 批量查询
        
        注意：query 为空时返回该 agent 的全量记忆
        """
        
        # 1. 构建需要查询的 agent 列表（自己 + 共享源）
        agent_ids_to_query = [agent_id]  # 自己
        shared_agent_ids = set()
        
        if include_shared:
            shared_source_agents = await MemorySharingRepository.get_agents_sharing_to(
                db, user_id, agent_id
            )
            agent_ids_to_query.extend(shared_source_agents)
            shared_agent_ids = set(shared_source_agents)
        
        # 2. 一次性调用 MemU 批量查询
        try:
            data = await self._memu_search(user_id, agent_ids_to_query, query)
        except Exception:
            return MemoryListResponse(memories=[], next_cursor=None, has_more=False)
        
        # 3. 转换结果，标记共享来源
        all_memories = self._convert_memu_list_with_sharing(data, agent_id, shared_agent_ids)
        
        # 4. 筛选类型
        if memory_type:
            all_memories = [m for m in all_memories if m.type == memory_type]
        
        # 5. 分页
        has_more = len(all_memories) > limit
        memories = all_memories[:limit]
        next_cursor = memories[-1].id if has_more and memories else None
        
        return MemoryListResponse(
            memories=memories,
            next_cursor=next_cursor,
            has_more=has_more
        )

    async def create_memory(
        self,
        user_id: str,
        agent_id: str,
        memory_type: str,
        content: str,
        title: Optional[str] = None
    ) -> MemoryResponse:
        """创建记忆"""
        summary = f"{title}: {content}" if title else content
        data = await self._memu_create(user_id, agent_id, memory_type, summary)
        return self._convert_to_memory_response(data, agent_id)

    async def update_memory(
        self,
        user_id: str,
        agent_id: str,
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> MemoryResponse:
        """更新记忆"""
        if title is None and content is None:
            raise BadRequestException("At least one field (title or content) is required")
        
        summary = f"{title}: {content}" if title and content else (content or title or "")
        data = await self._memu_update(user_id, agent_id, memory_id, summary)
        return self._convert_to_memory_response(data, agent_id)

    async def delete_memory(self, user_id: str, agent_id: str, memory_id: str) -> bool:
        """删除记忆"""
        await self._memu_delete(user_id, agent_id, memory_id)
        return True

    # ==================== Memory Sharing Config ====================

    async def get_memory_sharing(
        self,
        db: AsyncSession,
        user_id: str,
        agent_id: str
    ) -> MemorySharingConfig:
        """获取记忆共享配置"""
        config = await MemorySharingRepository.get_config(db, user_id, agent_id)
        
        if not config:
            return MemorySharingConfig(share_type="none", shared_with=[])
        
        shared_with = None
        if config.share_type == "specific":
            shared_with = await MemorySharingRepository.get_shared_with(db, config.id)
        
        return MemorySharingConfig(
            share_type=config.share_type,
            shared_with=shared_with
        )

    async def update_memory_sharing(
        self,
        db: AsyncSession,
        user_id: str,
        agent_id: str,
        share_type: str,
        shared_with: Optional[List[str]] = None
    ) -> MemorySharingConfig:
        """更新记忆共享配置"""
        if share_type not in ("none", "specific", "all"):
            raise BadRequestException("share_type must be one of: none, specific, all")

        if share_type == "specific" and not shared_with:
            raise BadRequestException("shared_with is required when share_type is 'specific'")

        # 更新数据库
        await MemorySharingRepository.upsert_config(
            db=db,
            user_id=user_id,
            agent_id=agent_id,
            share_type=share_type,
            shared_with=shared_with if share_type == "specific" else None
        )

        return MemorySharingConfig(
            share_type=share_type,
            shared_with=shared_with if share_type == "specific" else None
        )

    # ==================== 工具方法 ====================

    def _convert_to_memory_response(self, data: dict, agent_id: str, is_shared: bool = False, shared_from: Optional[str] = None) -> MemoryResponse:
        """将 MemU 响应转换为对外格式"""
        now = datetime.now().isoformat()
        return MemoryResponse(
            id=data.get("id") or data.get("memory_item_id", ""),
            agent_id=agent_id,
            type=data.get("memory_type", "profile"),
            title=None,
            content=data.get("summary", ""),
            created_at=datetime.fromisoformat(data.get("created_at", now).replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data.get("updated_at", now).replace("Z", "+00:00")),
            is_shared=is_shared,
            shared_from=shared_from
        )

    def _convert_memu_list_with_sharing(
        self, 
        data: dict, 
        current_agent_id: str, 
        shared_agent_ids: Set[str]
    ) -> List[MemoryResponse]:
        """将 MemU 批量查询结果转换为列表，自动标记共享来源"""
        items = data.get("memory_items", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []
        
        result = []
        for item in items:
            item_agent_id = item.get("agent_id", current_agent_id)
            is_shared = item_agent_id in shared_agent_ids
            shared_from = item_agent_id if is_shared else None
            result.append(self._convert_to_memory_response(item, item_agent_id, is_shared, shared_from))
        return result


memory_service = MemoryService()
