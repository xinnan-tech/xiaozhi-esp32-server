import json
import sys
import os
import asyncio
from datetime import datetime

from ..base import MemoryProviderBase, logger

TAG = __name__

# 添加 xiaozhi-memory 路径
XIAOZHI_MEMORY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../xiaozhi-memory"))
_MemoryManager = None

if os.path.exists(XIAOZHI_MEMORY_PATH):
    try:
        # 使用 importlib 来创建一个独立的命名空间，避免与 xiaozhi-server 的 core 包冲突
        import importlib.util

        # 将 xiaozhi-memory 添加到 sys.path
        if XIAOZHI_MEMORY_PATH not in sys.path:
            sys.path.insert(0, XIAOZHI_MEMORY_PATH)

        # 创建 xiaozhi_memory 命名空间
        if "xiaozhi_memory" not in sys.modules:
            # 创建一个虚拟的包模块
            import types
            xiaozhi_memory = types.ModuleType("xiaozhi_memory")
            xiaozhi_memory.__path__ = [XIAOZHI_MEMORY_PATH]
            sys.modules["xiaozhi_memory"] = xiaozhi_memory

            # 逐个加载子模块，建立正确的父子关系
            # 1. 加载 memories.base (被 core.memory_manager 依赖)
            memories_base_path = os.path.join(XIAOZHI_MEMORY_PATH, "memories", "base.py")
            if os.path.exists(memories_base_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.memories.base", memories_base_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.memories.base"] = module
                memories_module = types.ModuleType("xiaozhi_memory.memories")
                memories_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "memories")]
                memories_module.__package__ = "xiaozhi_memory"
                memories_module.base = module
                sys.modules["xiaozhi_memory.memories"] = memories_module
                spec.loader.exec_module(module)

            # 2. 加载 stores.sqlite_store (被 core.memory_manager 依赖)
            sqlite_path = os.path.join(XIAOZHI_MEMORY_PATH, "stores", "sqlite_store.py")
            if os.path.exists(sqlite_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.stores.sqlite_store", sqlite_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.stores.sqlite_store"] = module
                stores_module = types.ModuleType("xiaozhi_memory.stores")
                stores_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "stores")]
                stores_module.__package__ = "xiaozhi_memory"
                stores_module.sqlite_store = module
                sys.modules["xiaozhi_memory.stores"] = stores_module
                spec.loader.exec_module(module)

            # 3. 加载 utils.time_parser (被 core.memory_manager 依赖)
            time_parser_path = os.path.join(XIAOZHI_MEMORY_PATH, "utils", "time_parser.py")
            if os.path.exists(time_parser_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.utils.time_parser", time_parser_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.utils.time_parser"] = module
                utils_module = types.ModuleType("xiaozhi_memory.utils")
                utils_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "utils")]
                utils_module.__package__ = "xiaozhi_memory"
                utils_module.time_parser = module
                sys.modules["xiaozhi_memory.utils"] = utils_module
                spec.loader.exec_module(module)

            # 4. 加载 utils.tokenizer (被 core.retriever.fts 依赖)
            tokenizer_path = os.path.join(XIAOZHI_MEMORY_PATH, "utils", "tokenizer.py")
            if os.path.exists(tokenizer_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.utils.tokenizer", tokenizer_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.utils.tokenizer"] = module
                if "xiaozhi_memory.utils" not in sys.modules:
                    utils_module = types.ModuleType("xiaozhi_memory.utils")
                    utils_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "utils")]
                    utils_module.__package__ = "xiaozhi_memory"
                    sys.modules["xiaozhi_memory.utils"] = utils_module
                sys.modules["xiaozhi_memory.utils"].tokenizer = module
                spec.loader.exec_module(module)

            # 5. 加载 core.retriever.fts (被 core.memory_manager 依赖)
            fts_path = os.path.join(XIAOZHI_MEMORY_PATH, "core", "retriever", "fts.py")
            if os.path.exists(fts_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.core.retriever.fts", fts_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.core.retriever.fts"] = module
                retriever_module = types.ModuleType("xiaozhi_memory.core.retriever")
                retriever_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "core", "retriever")]
                retriever_module.__package__ = "xiaozhi_memory.core"
                retriever_module.fts = module
                sys.modules["xiaozhi_memory.core.retriever"] = retriever_module
                module.__package__ = "xiaozhi_memory.core.retriever"
                spec.loader.exec_module(module)
                spec.loader.exec_module(module)

            # 6. 加载 llm.base (被 llm.openai_client 依赖)
            llm_base_path = os.path.join(XIAOZHI_MEMORY_PATH, "llm", "base.py")
            if os.path.exists(llm_base_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.llm.base", llm_base_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.llm.base"] = module
                llm_module = types.ModuleType("xiaozhi_memory.llm")
                llm_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "llm")]
                llm_module.__package__ = "xiaozhi_memory"
                llm_module.base = module
                sys.modules["xiaozhi_memory.llm"] = llm_module
                module.__package__ = "xiaozhi_memory.llm"
                spec.loader.exec_module(module)

            # 6.1 加载 llm.openai_client (被 core.memory_manager._init_llm_client 使用)
            openai_client_path = os.path.join(XIAOZHI_MEMORY_PATH, "llm", "openai_client.py")
            if os.path.exists(openai_client_path):
                spec = importlib.util.spec_from_file_location("xiaozhi_memory.llm.openai_client", openai_client_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["xiaozhi_memory.llm.openai_client"] = module
                if "xiaozhi_memory.llm" not in sys.modules:
                    llm_module = types.ModuleType("xiaozhi_memory.llm")
                    llm_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "llm")]
                    llm_module.__package__ = "xiaozhi_memory"
                    sys.modules["xiaozhi_memory.llm"] = llm_module
                sys.modules["xiaozhi_memory.llm"].openai_client = module
                module.__package__ = "xiaozhi_memory.llm"
                spec.loader.exec_module(module)

            # 7. 最后加载 core.memory_manager
            mm_path = os.path.join(XIAOZHI_MEMORY_PATH, "core", "memory_manager.py")
            spec = importlib.util.spec_from_file_location("xiaozhi_memory.core.memory_manager", mm_path)
            mm_module = importlib.util.module_from_spec(spec)
            sys.modules["xiaozhi_memory.core.memory_manager"] = mm_module

            # 创建 core 包模块，需要设置 __path__ 使其成为包
            core_module = types.ModuleType("xiaozhi_memory.core")
            core_module.__path__ = [os.path.join(XIAOZHI_MEMORY_PATH, "core")]
            core_module.__package__ = "xiaozhi_memory"
            core_module.memory_manager = mm_module

            # 将 retriever 子模块添加为属性
            if "xiaozhi_memory.core.retriever" in sys.modules:
                core_module.retriever = sys.modules["xiaozhi_memory.core.retriever"]

            sys.modules["xiaozhi_memory.core"] = core_module

            # 设置模块的 __package__ 属性，使相对导入工作
            mm_module.__package__ = "xiaozhi_memory.core"

            # 在执行 memory_manager 之前，设置别名使其内部的 import 能工作
            # memory_manager.py 有 "from core.retriever.fts import FTS5Retriever"
            # 我们需要临时让 "core" 指向 xiaozhi_memory.core
            original_core = sys.modules.get("core")
            original_memories = sys.modules.get("memories")
            original_stores = sys.modules.get("stores")
            original_utils = sys.modules.get("utils")
            original_llm = sys.modules.get("llm")

            try:
                # 设置临时别名
                sys.modules["core"] = sys.modules["xiaozhi_memory.core"]
                sys.modules["memories"] = sys.modules["xiaozhi_memory.memories"]
                sys.modules["stores"] = sys.modules["xiaozhi_memory.stores"]
                sys.modules["utils"] = sys.modules["xiaozhi_memory.utils"]
                sys.modules["llm"] = sys.modules["xiaozhi_memory.llm"]

                # 现在执行模块，它内部的 import 应该能找到我们预先加载的模块
                spec.loader.exec_module(mm_module)

                _MemoryManager = mm_module.MemoryManager
                logger.bind(tag=TAG).info("xiaozhi-memory 加载成功")
            finally:
                # 恢复原始模块（如果有）
                if original_core is not None:
                    sys.modules["core"] = original_core
                elif "core" in sys.modules and sys.modules["core"] is sys.modules.get("xiaozhi_memory.core"):
                    sys.modules.pop("core", None)

                if original_memories is not None:
                    sys.modules["memories"] = original_memories
                elif "memories" in sys.modules and sys.modules["memories"] is sys.modules.get("xiaozhi_memory.memories"):
                    sys.modules.pop("memories", None)

                if original_stores is not None:
                    sys.modules["stores"] = original_stores
                elif "stores" in sys.modules and sys.modules["stores"] is sys.modules.get("xiaozhi_memory.stores"):
                    sys.modules.pop("stores", None)

                if original_utils is not None:
                    sys.modules["utils"] = original_utils
                elif "utils" in sys.modules and sys.modules["utils"] is sys.modules.get("xiaozhi_memory.utils"):
                    sys.modules.pop("utils", None)

                if original_llm is not None:
                    sys.modules["llm"] = original_llm
                elif "llm" in sys.modules and sys.modules["llm"] is sys.modules.get("xiaozhi_memory.llm"):
                    sys.modules.pop("llm", None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"加载 xiaozhi-memory 失败: {e}")
        import traceback
        logger.bind(tag=TAG).error(traceback.format_exc())


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.db_path = config.get("db_path", "./data/xiaozhi_memory.db")
        self.manager = None

        try:
            if _MemoryManager is None:
                raise ImportError("xiaozhi-memory 未安装或加载失败")

            cfg = {
                "retrieval_mode": config.get("retrieval_mode", "fts5"),
                "sqlite": {"path": self.db_path},
                "llm": config.get("llm", {}),
                "extraction": config.get("extraction", {"enabled": False})
            }

            # MemoryManager.__init__ 内部有 "from core.retriever.fts import FTS5Retriever"
            # 需要临时设置模块别名，使其能找到我们加载的模块
            original_core = sys.modules.get("core")
            original_memories = sys.modules.get("memories")
            original_stores = sys.modules.get("stores")
            original_utils = sys.modules.get("utils")
            original_llm = sys.modules.get("llm")

            try:
                # 设置临时别名，指向 xiaozhi_memory 命名空间下的模块
                sys.modules["core"] = sys.modules.get("xiaozhi_memory.core")
                sys.modules["memories"] = sys.modules.get("xiaozhi_memory.memories")
                sys.modules["stores"] = sys.modules.get("xiaozhi_memory.stores")
                sys.modules["utils"] = sys.modules.get("xiaozhi_memory.utils")
                sys.modules["llm"] = sys.modules.get("xiaozhi_memory.llm")

                # 创建 MemoryManager 实例（此时会执行其 __init__ 中的 import）
                self.manager = _MemoryManager(cfg)
                logger.bind(tag=TAG).info(f"成功初始化 aipet 记忆服务: {self.db_path}")
            finally:
                # 恢复原始模块
                if original_core is not None:
                    sys.modules["core"] = original_core
                elif "core" in sys.modules and sys.modules["core"] is sys.modules.get("xiaozhi_memory.core"):
                    sys.modules.pop("core", None)

                if original_memories is not None:
                    sys.modules["memories"] = original_memories
                elif "memories" in sys.modules and sys.modules["memories"] is sys.modules.get("xiaozhi_memory.memories"):
                    sys.modules.pop("memories", None)

                if original_stores is not None:
                    sys.modules["stores"] = original_stores
                elif "stores" in sys.modules and sys.modules["stores"] is sys.modules.get("xiaozhi_memory.stores"):
                    sys.modules.pop("stores", None)

                if original_utils is not None:
                    sys.modules["utils"] = original_utils
                elif "utils" in sys.modules and sys.modules["utils"] is sys.modules.get("xiaozhi_memory.utils"):
                    sys.modules.pop("utils", None)

                if original_llm is not None:
                    sys.modules["llm"] = original_llm
                elif "llm" in sys.modules and sys.modules["llm"] is sys.modules.get("xiaozhi_memory.llm"):
                    sys.modules.pop("llm", None)

        except ImportError as e:
            logger.bind(tag=TAG).error(f"xiaozhi-memory 未安装: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"初始化 aipet 记忆服务失败: {e}")

    async def save_memory(self, msgs, session_id=None):
        """保存记忆"""
        if not self.manager or not self.role_id:
            return

        try:
            # 格式化消息
            messages = []
            for msg in msgs:
                if msg.role in ("system", "tool"):
                    continue

                content = msg.content
                if not content:
                    continue

                # Extract content from JSON format if present (for ASR with emotion/language tags)
                # Same logic as in query_memory method
                try:
                    if content and content.strip().startswith("{") and content.strip().endswith("}"):
                        data = json.loads(content)
                        if "content" in data:
                            content = data["content"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    # If parsing fails, use original content
                    pass

                messages.append({"role": msg.role, "content": content})

            result = self.manager.add_memory(messages, user_id=self.role_id)
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")

        return None

    async def query_memory(self, query: str) -> str:
        if not self.manager:
            return ""

        try:
            if not getattr(self, "role_id", None):
                return ""

            search_query = query
            try:
                if query.strip().startswith("{") and query.strip().endswith("}"):
                    data = json.loads(query)
                    if "content" in data:
                        search_query = data["content"]
            except (json.JSONDecodeError, KeyError):
                pass

            memories = self.manager.retrieve_memories(
                query=search_query,
                user_id=self.role_id,
                limit=5
            )

            if not memories:
                return ""

            # Format each memory entry
            memories_str = "\n".join([f"- {m}" for m in memories])
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""
