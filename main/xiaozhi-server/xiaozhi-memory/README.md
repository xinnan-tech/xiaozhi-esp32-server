# 小智记忆框架 (XiaoZhi Memory Framework)

轻量级AI记忆系统，支持多种检索模式。

## 特性

- ✅ **轻量优先**: SQLite + FTS5，无需额外依赖
- ✅ **中文友好**: jieba分词 + 保持原文语言
- ✅ **智能管理**: 支持增删改查和遗忘机制
- ✅ **意图感知**: 专门处理未来计划和状态管理
- ✅ **渐进式**: 从FTS5开始，可升级到Embedding
- ✅ **可扩展**: 预留混合检索和高级功能接口

## 检索模式

| 模式 | 存储方式 | 检索方式 | 适用场景 |
|------|----------|----------|----------|
| **FTS5** | SQLite | BM25全文检索 | 轻量级、离线部署 |
| **Embedding** | ChromaDB | 语义向量 | 语义理解 |
| **Hybrid** | 两者结合 | RRF融合 | 最佳效果 |

## 安装

```bash
# 基础依赖（FTS5模式）
pip install jieba pydantic

# 完整依赖（包含Embedding）
pip install jieba pydantic chromadb sentence-transformers
```

## 快速开始

```python
from xiaozhi_memory import MemoryManager

# 初始化（FTS5模式）
manager = MemoryManager({
    "retrieval_mode": "fts5",
    "sqlite": {"path": "./data/xiaozhi_memory.db"},
    "llm": {"provider": "ollama", "model": "qwen2:7b"}
})

# 添加记忆
await manager.add_memory([
    {"role": "user", "content": "我两天后要去北京开会"}
], user_id="user123")

# 搜索记忆
results = await manager.search("北京", user_id="user123")

# 获取未来计划
intentions = await manager.get_upcoming_intentions("user123", days=7)
```

## 项目结构

```
xiaozhi-memory/
├── core/
│   ├── memory_manager.py      # 核心记忆管理器
│   └── retriever/             # 检索器
├── stores/                    # 存储层
├── memories/                  # 记忆模型
├── prompts/                   # 提示词
├── utils/                     # 工具函数
└── api/                       # API接口
```

## 配置

见 `config.yaml` 或 [设计文档](../analysis/XiaoZhi-Memory-Design.md)。

## 许可证

MIT License
