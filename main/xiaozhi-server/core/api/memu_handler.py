from aiohttp import web
from core.api.base_handler import BaseHandler
from config.logger import setup_logging

TAG = __name__


class MemuHandler(BaseHandler):
    """MEMu 记忆管理 API 处理器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = setup_logging()
        self.memu_client = None
        self.user_id_aliases = {}
        self.default_user_id = None
        self.default_agent_id = "xiaozhi_agent"
        
        # 初始化 MEMu 客户端
        self._init_memu_client()

    def _init_memu_client(self):
        """初始化 MEMu 客户端
        
        注意：记忆管理页面独立于系统的记忆模块配置
        只要配置了 MEMu API Key，就可以使用记忆管理功能
        从 custom_config.yaml 直接读取 MEMu 配置
        """
        try:
            # 从 custom_config.yaml 文件直接读取 MEMu 配置
            import os
            import yaml
            from pathlib import Path
            
            # 获取项目根目录
            project_dir = Path(__file__).parent.parent.parent
            custom_config_path = project_dir / "custom_config.yaml"
            
            if not custom_config_path.exists():
                self.logger.bind(tag=TAG).warning(f"custom_config.yaml 文件不存在: {custom_config_path}")
                return
            
            with open(custom_config_path, "r", encoding="utf-8") as f:
                custom_config = yaml.safe_load(f)
            
            memory_module_config = custom_config.get("Memory", {}).get("memu", {})
            if memory_module_config:
                from memu import MemuClient

                self.default_agent_id = memory_module_config.get("default_agent_id", self.default_agent_id)
                self.default_user_id = self._standardize_id(memory_module_config.get("default_user_id"))
                alias_config = memory_module_config.get("user_id_aliases", {}) or {}
                self.user_id_aliases = {
                    self._standardize_id(alias): self._standardize_id(real_id)
                    for alias, real_id in alias_config.items()
                    if alias and real_id
                }

                api_key = memory_module_config.get("api_key", "")
                base_url = memory_module_config.get("base_url", "https://api.memu.so")
                
                if api_key and "你" not in api_key:
                    self.memu_client = MemuClient(
                        base_url=base_url,
                        api_key=api_key
                    )
                    self.logger.bind(tag=TAG).info("MEMu 客户端初始化成功（记忆管理 API）")
                else:
                    self.logger.bind(tag=TAG).warning("MEMu API Key 未配置或无效")
            else:
                self.logger.bind(tag=TAG).warning("custom_config.yaml 中未找到 Memory.memu 配置")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化 MEMu 客户端失败: {e}")

    async def handle_options(self, request):
        """处理 OPTIONS 请求（CORS 预检）"""
        response = web.Response()
        self._add_cors_headers(response)
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    async def handle_post(self, request):
        """处理 POST 请求"""
        response = None
        
        try:
            # 检查 MEMu 客户端是否可用
            if not self.memu_client:
                response = web.json_response({
                    "success": False,
                    "error": "MEMu 服务未配置或未启用"
                })
                self._add_cors_headers(response)
                return response

            # 解析请求数据
            try:
                data = await request.json()
            except Exception as e:
                response = web.json_response({
                    "success": False,
                    "error": f"请求数据格式错误: {str(e)}"
                })
                self._add_cors_headers(response)
                return response

            action = data.get("action")
            user_id = self._normalize_user_id(data.get("user_id"))
            agent_id = data.get("agent_id") or self.default_agent_id

            if not user_id:
                response = web.json_response({
                    "success": False,
                    "error": "缺少 user_id 参数"
                })
                self._add_cors_headers(response)
                return response

            # 根据不同的 action 执行相应操作
            if action == "get_all":
                result = await self._get_all_memories(user_id, agent_id)
            elif action == "search":
                query = data.get("query")
                top_k = data.get("top_k", 10)
                result = await self._search_memories(user_id, agent_id, query, top_k)
            elif action == "get_categories":
                topic = data.get("topic")
                top_k = data.get("top_k", 5)
                result = await self._get_categories(user_id, agent_id, topic, top_k)
            elif action == "get_by_session":
                session_id = data.get("session_id")
                result = await self._get_memories_by_session(user_id, agent_id, session_id)
            elif action == "delete":
                result = await self._delete_memories(user_id, agent_id)
            else:
                result = {
                    "success": False,
                    "error": f"未知操作: {action}"
                }

            response = web.json_response(result)
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理请求时发生错误: {e}")
            response = web.json_response({
                "success": False,
                "error": str(e)
            })
            self._add_cors_headers(response)
            return response

    async def _get_all_memories(self, user_id: str, agent_id: str = None):
        """获取所有记忆"""
        try:
            # 尝试使用新版API参数，如果失败则使用旧版API
            try:
                result = self.memu_client.retrieve_default_categories(
                    user_id=user_id,
                    agent_id=agent_id,
                    want_memory_items=True
                )
            except TypeError:
                # 旧版本不支持want_memory_items参数
                self.logger.bind(tag=TAG).warning("MEMu API不支持want_memory_items参数，使用默认方式获取")
                result = self.memu_client.retrieve_default_categories(
                    user_id=user_id,
                    agent_id=agent_id
                )
            
            # 将MEMu对象转换为可序列化的字典
            data = self._convert_to_dict(result)
            
            # 处理返回的数据结构
            # MEMu API 返回格式: {"categories": [...], "total_categories": N}
            categories_list = []
            if isinstance(data, dict) and "categories" in data:
                categories_list = data["categories"]
            elif isinstance(data, list):
                categories_list = data
            
            # 解析并规范化分类数据
            normalized_categories = []
            for category in categories_list:
                # 处理 memory_items 字段（可能为 None 或数组）
                memory_items = category.get("memory_items") or category.get("memories") or []
                
                # 规范化记忆项
                normalized_memories = []
                if memory_items and isinstance(memory_items, list):
                    for memory in memory_items:
                        # 确保每个记忆项都有 metadata 字段
                        if isinstance(memory, dict) and "metadata" not in memory:
                            memory["metadata"] = {}
                        normalized_memories.append(memory)
                
                # 创建规范化的分类对象
                normalized_category = {
                    "name": category.get("name", "未分类"),
                    "type": category.get("type", "auto"),
                    "description": category.get("description", ""),
                    "summary": category.get("summary", ""),
                    "count": len(normalized_memories),
                    "memories": normalized_memories,  # 统一使用 memories 字段名
                }
                normalized_categories.append(normalized_category)
            
            return {
                "success": True,
                "data": normalized_categories,
                "message": "获取记忆成功"
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取所有记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _standardize_id(self, value):
        if not value:
            return None
        normalized = str(value).strip()
        if ":" in normalized:
            normalized = normalized.upper()
        return normalized or None

    def _normalize_user_id(self, user_id):
        normalized = self._standardize_id(user_id)
        if not normalized:
            return self.default_user_id
        if normalized in self.user_id_aliases:
            alias_target = self.user_id_aliases[normalized]
            self.logger.bind(tag=TAG).info(f"使用 user_id 别名映射: {normalized} -> {alias_target}")
            return alias_target
        # 当仍使用默认占位值时，尝试 fallback
        if normalized in {"XIAOZHI-WEB-TEST", "TEST-DEVICE-WEB"} and self.default_user_id:
            self.logger.bind(tag=TAG).info(f"使用默认 user_id: {self.default_user_id}")
            return self.default_user_id
        return normalized

    async def _search_memories(self, user_id: str, agent_id: str, query: str, top_k: int):
        """搜索记忆"""
        try:
            if not query:
                return {
                    "success": False,
                    "error": "缺少 query 参数"
                }
            
            result = self.memu_client.retrieve_related_memory_items(
                user_id=user_id,
                agent_id=agent_id,
                query=query,
                top_k=top_k,
                min_similarity=0.3
            )
            
            # 将MEMu对象转换为可序列化的字典
            data = self._convert_to_dict(result)
            
            # 提取 related_memories 列表（SDK 返回结构为 {related_memories: [...], query: ..., total_found: N}）
            memories = []
            if isinstance(data, dict):
                memories = data.get("related_memories", [])
            elif isinstance(data, list):
                memories = data
            
            # 确保 metadata 被正确返回
            for memory in memories:
                if isinstance(memory, dict) and "metadata" not in memory:
                    memory["metadata"] = {}
            
            return {
                "success": True,
                "data": memories,
                "message": f"搜索成功，找到 {len(memories)} 条记忆"
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"搜索记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_categories(self, user_id: str, agent_id: str, topic: str, top_k: int):
        """获取记忆分类"""
        try:
            if not topic:
                return {
                    "success": False,
                    "error": "缺少 topic 参数"
                }
            
            result = self.memu_client.retrieve_related_clustered_categories(
                user_id=user_id,
                agent_id=agent_id,
                category_query=topic,
                top_k=top_k,
                want_summary=True
            )
            
            # 将MEMu对象转换为可序列化的字典
            data = self._convert_to_dict(result)
            
            return {
                "success": True,
                "data": data,
                "message": f"获取分类成功，找到 {len(data) if data else 0} 个分类"
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取分类失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _delete_memories(self, user_id: str, agent_id: str = None):
        """删除记忆"""
        try:
            result = self.memu_client.delete_memories(
                user_id=user_id,
                agent_id=agent_id
            )
            
            # 将MEMu对象转换为可序列化的字典
            data = self._convert_to_dict(result)
            
            return {
                "success": True,
                "data": data,
                "message": "记忆删除成功"
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"删除记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _convert_to_dict(self, obj):
        """将MEMu对象转换为可JSON序列化的字典"""
        import json
        
        if obj is None:
            return None
        
        # 如果已经是基本类型，直接返回
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # 如果是列表，递归转换每个元素
        if isinstance(obj, list):
            return [self._convert_to_dict(item) for item in obj]
        
        # 如果是字典，递归转换每个值
        if isinstance(obj, dict):
            return {key: self._convert_to_dict(value) for key, value in obj.items()}
        
        # 如果是对象，尝试多种方式转换
        try:
            # 方法1: 尝试使用对象的dict()方法
            if hasattr(obj, 'dict'):
                return self._convert_to_dict(obj.dict())
            
            # 方法2: 尝试使用对象的model_dump()方法（pydantic v2）
            if hasattr(obj, 'model_dump'):
                return self._convert_to_dict(obj.model_dump())
            
            # 方法3: 尝试使用__dict__属性
            if hasattr(obj, '__dict__'):
                return self._convert_to_dict(obj.__dict__)
            
            # 方法4: 尝试转换为字符串
            return str(obj)
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"对象转换失败，使用字符串表示: {e}")
            return str(obj)

    async def _get_memories_by_session(self, user_id: str, agent_id: str, session_id: str):
        """根据session_id获取记忆"""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "缺少 session_id 参数"
                }
            
            # 获取所有记忆 - 兼容新旧版本API
            try:
                all_categories = self.memu_client.retrieve_default_categories(
                    user_id=user_id,
                    agent_id=agent_id,
                    want_memory_items=True
                )
            except TypeError:
                # 旧版本不支持want_memory_items参数
                self.logger.bind(tag=TAG).warning("MEMu API不支持want_memory_items参数，使用默认方式获取")
                all_categories = self.memu_client.retrieve_default_categories(
                    user_id=user_id,
                    agent_id=agent_id
                )
            
            # 将MEMu对象转换为可序列化的字典
            categories_data = self._convert_to_dict(all_categories)
            
            # 处理返回的数据结构
            categories_list = []
            if isinstance(categories_data, dict) and "categories" in categories_data:
                categories_list = categories_data["categories"]
            elif isinstance(categories_data, list):
                categories_list = categories_data
            
            # 筛选包含指定session_id的记忆
            filtered_memories = []
            for category in categories_list:
                # 处理 memory_items 字段（可能为 None 或数组）
                memory_items = category.get("memory_items") or category.get("memories") or []
                
                if memory_items and isinstance(memory_items, list):
                    for memory in memory_items:
                        metadata = memory.get("metadata", {})
                        if metadata.get("session_id") == session_id:
                            # 添加分类信息
                            memory["category_name"] = category.get("name", "未分类")
                            # 确保 metadata 存在
                            if "metadata" not in memory:
                                memory["metadata"] = metadata
                            filtered_memories.append(memory)
            
            return {
                "success": True,
                "data": filtered_memories,
                "message": f"找到 {len(filtered_memories)} 条与会话 {session_id} 相关的记忆"
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"按会话查询记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

