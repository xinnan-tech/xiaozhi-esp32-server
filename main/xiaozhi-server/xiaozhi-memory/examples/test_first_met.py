"""
测试第一次见面时间功能
"""
import asyncio
import sys
import os
import tempfile
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core import MemoryManager
from memories.base import UserProfile, MemoryType


async def test_first_met():
    """测试第一次见面时间功能"""
    print("=" * 60)
    print("第一次见面时间功能测试")
    print("=" * 60)

    # 使用临时数据库
    temp_db = tempfile.mktemp(suffix='.db')
    config = {
        "retrieval_mode": "fts5",
        "sqlite": {"path": temp_db}
    }

    try:
        manager = MemoryManager(config)
        device_id = "esp32_test_device"

        # 测试1: 首次见面
        print("\n1. 测试首次见面...")
        days = await manager.record_first_meeting(device_id)
        print(f"   互动天数: {days}")
        assert days == 1, "首次见面应该是第1天"

        # 获取用户画像
        profile = await manager.get_user_profile(device_id)
        assert profile is not None, "应该创建用户画像"
        assert profile.first_met is not None, "应该有第一次见面时间"
        assert profile.total_interaction_days == 1, "应该是第1天"
        print(f"   第一次见面时间: {profile.first_met}")
        print("   ✓ 首次见面记录成功")

        # 测试2: 再次见面（同一天）
        print("\n2. 测试同一天再次见面...")
        days = await manager.record_first_meeting(device_id)
        print(f"   互动天数: {days}")
        assert days == 1, "同一天内应该还是第1天"
        print("   ✓ 同一天内天数正确")

        # 测试3: 获取距离上次互动的天数
        print("\n3. 测试获取上次互动时间...")
        days_since = await manager.get_days_since_last_interaction(device_id)
        print(f"   距离上次互动: {days_since} 天")
        assert days_since == 0, "应该是0天（刚互动过）"
        print("   ✓ 上次互动时间正确")

        # 测试4: 创建或更新画像
        print("\n4. 测试创建或更新画像...")
        await manager.create_or_update_profile(device_id, {
            "name": "测试用户",
            "nickname": "小测",
            "location": "北京"
        })
        profile = await manager.get_user_profile(device_id)
        assert profile.name == "测试用户", "姓名应该更新"
        assert profile.nickname == "小测", "昵称应该更新"
        assert profile.first_met is not None, "第一次见面时间应该保留"
        print(f"   姓名: {profile.name}")
        print(f"   昵称: {profile.nickname}")
        print(f"   第一次见面: {profile.first_met}")
        print("   ✓ 画像更新成功")

        # 测试5: 直接验证数据库
        print("\n5. 验证数据库存储...")
        import sqlite3
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memories WHERE type = ?", (MemoryType.PROFILE.value,))
        rows = cursor.fetchall()
        print(f"   数据库中的画像数量: {len(rows)}")
        for row in rows:
            print(f"   - first_met: {row['first_met']}")
            print(f"   - total_interaction_days: {row['total_interaction_days']}")

        conn.close()

        manager.close()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        manager.close()
        raise
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        manager.close()
        raise
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


if __name__ == "__main__":
    asyncio.run(test_first_met())
