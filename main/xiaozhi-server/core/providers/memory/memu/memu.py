import traceback
from functools import wraps
from typing import Optional, Dict, Any, List, Callable

import requests

from ..base import MemoryProviderBase, logger
from memu import MemuClient
from core.utils.util import check_model_key

TAG = __name__

# 常量定义
DEFAULT_AGENT_ID = "xiaozhi_agent"
DEFAULT_BASE_URL = "https://api.memu.so"

# Category 到中文标题的映射
CATEGORY_TITLES = {
    "profiles": "用户画像",
    "events": "近期事件",
    "activities": "近期活动",
    "preferences": "用户偏好",
}


def require_memu(func: Callable) -> Callable:
    """装饰器：检查 MemU 服务是否可用"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.use_memu:
            return {"success": False, "error": "MemU 服务未启用"}
        return func(self, *args, **kwargs)
    return wrapper


class MemoryProvider(MemoryProviderBase):
    """MemU 记忆服务提供者"""

    def __init__(self, config: dict, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", DEFAULT_BASE_URL)
        self.user_name = config.get("user_name", "用户")
        self.agent_name = config.get("agent_name", "小智")
        self.agent_id = config.get("agent_id", DEFAULT_AGENT_ID)
        self.use_memu = False
        self.client = None

        model_key_msg = check_model_key("MemU", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            return

        try:
            self.client = MemuClient(base_url=self.base_url, api_key=self.api_key)
            self.use_memu = True
            logger.bind(tag=TAG).info("成功连接到 MemU 服务")
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接 MemU 服务失败: {e}")
            logger.bind(tag=TAG).debug(traceback.format_exc())

    # ==================== 内部工具方法 ====================

    @property
    def _headers(self) -> Dict[str, str]:
        """构造请求头"""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    def _base_payload(self, **extra) -> Dict[str, Any]:
        """构造基础请求体，包含 user_id 和 agent_id"""
        payload = {"user_id": self.role_id, "agent_id": self.agent_id}
        payload.update(extra)
        return payload

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """统一的 HTTP 请求方法"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                params=params,
                headers=self._headers,
                timeout=30
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.bind(tag=TAG).error(f"请求失败 [{method} {endpoint}]: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.bind(tag=TAG).error(f"请求异常 [{method} {endpoint}]: {e}")
            return {"success": False, "error": str(e)}

    async def save_memory(self, msgs, context=None):
        if not self.use_memu:
            return None
        if len(msgs) < 2:
            return None

        try:
            # Format the conversation as a single text string for memU
            conversation_text = ""
            for message in msgs:
                if message.role == "system":
                    continue
                role_name = self.user_name if message.role == "user" else self.agent_name
                conversation_text += f"{role_name}: {message.content}\n"

            if not conversation_text.strip():
                return None

            # 准备session_date参数（MEMu SDK支持的参数）
            import time
            from datetime import datetime
            
            session_date = None
            context_info = {}
            # 优先从 context 获取 agent_id，否则用 self.agent_id
            agent_id = self.agent_id
            if context:
                # 记录上下文信息到日志
                if "session_id" in context:
                    context_info["session_id"] = context["session_id"]
                if "mac_address" in context:
                    context_info["mac_address"] = context["mac_address"]
                if "device_id" in context:
                    context_info["device_id"] = context["device_id"]
                if "agent_id" in context and context["agent_id"]:
                    agent_id = context["agent_id"]
                    context_info["agent_id"] = agent_id
                
                # 使用当前时间作为session_date
                session_date = datetime.now().strftime("%Y-%m-%d")
            
            # Use memorize_conversation to store the memory
            result = self.client.memorize_conversation(
                conversation=conversation_text.strip(),
                user_id=self.role_id,
                user_name=self.user_name,
                agent_id=agent_id,
                agent_name=self.agent_name,
                session_date=session_date
            )
            logger.bind(tag=TAG).info(f"保存记忆成功，context: {context_info}, session_date: {session_date}")
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.use_memu:
            return ""
        try:
            # Use retrieve_related_memory_items to retrieve memories
            results = self.client.retrieve_related_memory_items(
                user_id=self.role_id,
                agent_id=self.agent_id,
                query=query,
                top_k=10,
                min_similarity=0.3
            )

            # 转换结果
            if hasattr(results, 'model_dump'):
                data = results.model_dump()
            elif hasattr(results, 'dict'):
                data = results.dict() if callable(results.dict) else results
            else:
                data = results
            
            # 检查是否有记忆项（兼容新旧 API 格式）
            memory_items = []
            if isinstance(data, dict):
                # 优先使用 related_memories（新 API 格式）
                if 'related_memories' in data:
                    memory_items = data['related_memories']
                elif 'memory_items' in data:
                    memory_items = data['memory_items']
            elif isinstance(data, list):
                memory_items = data

            if not memory_items:
                return ""

            # 按 category 分组
            grouped = {
                "profiles": [],
                "events": [],
                "activities": [],
                "preferences": [],
                "other": []
            }
            
            for entry in memory_items:
                # 转换 entry 为字典
                if hasattr(entry, 'model_dump'):
                    entry_dict = entry.model_dump()
                elif hasattr(entry, 'dict'):
                    entry_dict = entry.dict() if callable(entry.dict) else entry
                else:
                    entry_dict = entry
                
                # 解析嵌套的 memory 对象（新 API 格式）
                memory_obj = entry_dict.get("memory", entry_dict)
                if hasattr(memory_obj, 'model_dump'):
                    memory_obj = memory_obj.model_dump()
                elif hasattr(memory_obj, 'dict'):
                    memory_obj = memory_obj.dict() if callable(memory_obj.dict) else memory_obj
                
                # 提取字段
                category = memory_obj.get("category", "other")
                content = memory_obj.get("content", "") or memory_obj.get("memory", "")
                # 事件类使用 happened_at，其他用 created_at
                timestamp = memory_obj.get("happened_at") or memory_obj.get("created_at", "")
                
                if not content:
                    continue
                
                # 分组
                if category in grouped:
                    grouped[category].append((timestamp, content))
                else:
                    grouped["other"].append((timestamp, content))

            # 格式化分组输出
            output = []
            for category, title in CATEGORY_TITLES.items():
                items = grouped.get(category, [])
                if not items:
                    continue
                
                output.append(f"## {title}")
                
                # 按时间倒序排列
                items.sort(key=lambda x: x[0] or "", reverse=True)
                
                # 每类最多 5 条
                for ts, content in items[:5]:
                    if category in ("events", "activities") and ts:
                        # 格式化时间戳
                        try:
                            dt = ts.split(".")[0]  # Remove milliseconds
                            formatted_time = dt.replace("T", " ").split(" ")[0]  # 只保留日期
                        except:
                            formatted_time = ts
                        output.append(f"- [{formatted_time}] {content}")
                    else:
                        output.append(f"- {content}")
            
            # 处理 other 分类（如果有）
            other_items = grouped.get("other", [])
            if other_items:
                output.append("## 其他")
                other_items.sort(key=lambda x: x[0] or "", reverse=True)
                for ts, content in other_items[:5]:
                    output.append(f"- {content}")

            if not output:
                return ""

            memories_str = "\n".join(output)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            return ""

    # ==================== Memory Item CRUD ====================

    @require_memu
    def create_memory_item(self, memory_type: str, summary: str) -> Dict[str, Any]:
        """创建单条记忆记录
        
        Args:
            memory_type: 记忆类型
            summary: 记忆摘要内容
        """
        payload = self._base_payload(memory_type=memory_type, summary=summary)
        return self._request("POST", "/memory-items", payload=payload)

    @require_memu
    def update_memory_item(self, memory_item_id: str, summary: str) -> Dict[str, Any]:
        """修改单条记忆记录
        
        Args:
            memory_item_id: 记忆记录 ID
            summary: 新的摘要内容
        """
        payload = self._base_payload(summary=summary)
        return self._request("PUT", f"/memory-items/{memory_item_id}", payload=payload)

    @require_memu
    def delete_memory_item(self, memory_item_id: str) -> Dict[str, Any]:
        """删除单条记忆记录
        
        Args:
            memory_item_id: 记忆记录 ID
        """
        params = {"user_id": self.role_id, "agent_id": self.agent_id}
        return self._request("DELETE", f"/memory-items/{memory_item_id}", params=params)

