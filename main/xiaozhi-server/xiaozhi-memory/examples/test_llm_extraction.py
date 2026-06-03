"""
LLM 记忆提取测试

支持火山引擎豆包、OpenAI 等兼容 OpenAI API 格式的服务
"""
import asyncio
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_manager import MemoryManager


async def test_llm_extraction():
    """测试 LLM 记忆提取功能"""

    # 默认使用火山引擎豆包配置
    config = {
        "retrieval_mode": "fts5",
        "sqlite": {"path": "./data/test_llm_memory.db"},
        "llm": {
            "provider": "openai",
            # 火山引擎豆包（默认）
            "api_key": os.getenv("ARK_API_KEY", "6202d63d-377b-4bd7-a2ad-c162ed977c24"),
            "model": os.getenv("ARK_MODEL", "doubao-seed-2-0-lite-260428"),
            "base_url": os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),

            # OpenAI 官方（取消注释使用）
            # "api_key": os.getenv("OPENAI_API_KEY", ""),
            # "model": "gpt-4o-mini",
            # "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        },
        "extraction": {
            "enabled": True,
            "max_retrieved_memories": 20,
            "max_recent_memories": 10,
            "observation_date_delta": 0
        }
    }

    if not config["llm"]["api_key"]:
        print("错误: 请设置 API Key")
        print("火山引擎: export ARK_API_KEY=your-api-key")
        print("OpenAI: export OPENAI_API_KEY=your-api-key")
        return

    # 创建管理器
    manager = MemoryManager(config)

    print("=== 测试 LLM 记忆提取 ===\n")

    # 测试对话
    messages = [
        {"role": "user", "content": "我叫张三，是一名软件工程师，住在北京"},
        {"role": "assistant", "content": "你好张三！很高兴认识你。"},
        {"role": "user", "content": "我明天下午3点要和客户李四开会，讨论新项目的技术方案"},
        {"role": "user", "content": "我喜欢喝咖啡，每天早上都要来一杯拿铁"},
    ]

    print("输入对话:")
    for msg in messages:
        print(f"  {msg['role']}: {msg['content']}")
    print()

    # 添加记忆
    result = await manager.add_memory(messages, "test_user_llm")
    print(f"提取结果: {result}")
    print()

    # 查看提取的记忆
    memories = await manager.get_all_memories("test_user_llm")
    print(f"共提取了 {len(memories)} 条记忆:\n")
    for m in memories:
        print(f"- [{m.type.value}] {m.content}")
        if hasattr(m, 'planned_time') and m.planned_time:
            print(f"  计划时间: {m.planned_time}")
        if m.time_info:
            print(f"  时间信息: {m.time_info}")
        print()

    # 测试搜索
    print("=== 测试搜索 ===")
    query = "开会"
    results = await manager.search(query, "test_user_llm", top_k=3)
    print(f"搜索 '{query}' 的结果:")
    for m in results:
        print(f"- {m.content}")
    print()

    # 测试即将到来的意图
    print("=== 测试即将到来的意图 ===")
    intentions = await manager.get_upcoming_intentions("test_user_llm", days=7)
    print(f"未来7天的意图:")
    for intent in intentions:
        print(f"- {intent.content}")
        if intent.planned_time:
            print(f"  计划时间: {intent.planned_time}")
    print()

    # 关闭
    manager.close()
    print("测试完成!")


if __name__ == "__main__":
    asyncio.run(test_llm_extraction())
