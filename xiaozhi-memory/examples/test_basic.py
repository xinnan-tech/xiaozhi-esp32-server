"""
测试脚本
"""
import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core import MemoryManager
from memories import IntentionStatus


async def test_basic():
    """基础功能测试"""
    print("=" * 50)
    print("小智记忆框架 - 基础测试")
    print("=" * 50)

    # 初始化
    config = {
        "retrieval_mode": "fts5",
        "sqlite": {"path": "./data/test_memory.db"}
    }

    manager = MemoryManager(config)
    user_id = "test_user"

    # 1. 添加记忆
    print("\n1. 添加记忆...")
    messages = [
        {"role": "user", "content": "我叫张三，是一名软件工程师"},
        {"role": "user", "content": "我两天后要去北京开会"},
        {"role": "user", "content": "我喜欢喝咖啡，特别是拿铁"},
        {"role": "user", "content": "明天下午3点要和客户李四开会"}
    ]

    result = await manager.add_memory(messages, user_id)
    print(f"   添加结果: {result}")

    # 2. 搜索记忆
    print("\n2. 搜索记忆...")
    results = await manager.search("北京", user_id)
    print(f"   搜索'北京'找到 {len(results)} 条:")
    for m in results:
        print(f"   - {m.content}")

    # 3. 获取未来计划
    print("\n3. 获取未来计划...")
    intentions = await manager.get_upcoming_intentions(user_id, days=7)
    print(f"   未来7天有 {len(intentions)} 个计划:")
    for intent in intentions:
        print(f"   - {intent.content}")
        if intent.planned_time:
            print(f"     计划时间: {intent.planned_time}")

    # 4. 更新意图状态
    print("\n4. 更新意图状态...")
    if intentions:
        intent_id = intentions[0].id
        success = await manager.update_intention_status(intent_id, IntentionStatus.COMPLETED)
        print(f"   更新结果: {success}")

    # 5. 获取所有记忆
    print("\n5. 获取所有记忆...")
    all_memories = await manager.get_all_memories(user_id)
    print(f"   共有 {len(all_memories)} 条记忆:")
    for m in all_memories:
        print(f"   - [{m.type.value}] {m.content}")

    # 清理
    manager.close()
    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(test_basic())
