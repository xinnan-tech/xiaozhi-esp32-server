"""
MEMu Memory Provider 单元测试

测试目标:
- query_memory 正确解析 related_memories 和 memory_items 格式
- query_memory 按 category 正确分组
- query_memory 格式化输出符合预期
- agent_id 处理逻辑正确
"""

import unittest


# ==================== 核心逻辑函数（从 memu.py 提取用于测试） ====================

CATEGORY_TITLES = {
    "profiles": "用户画像",
    "events": "近期事件",
    "activities": "近期活动",
    "preferences": "用户偏好",
}


def parse_memory_items(data: dict) -> list:
    """解析 API 返回的记忆项（兼容新旧格式）"""
    memory_items = []
    if isinstance(data, dict):
        if 'related_memories' in data:
            memory_items = data['related_memories']
        elif 'memory_items' in data:
            memory_items = data['memory_items']
    elif isinstance(data, list):
        memory_items = data
    return memory_items


def group_memories_by_category(memory_items: list) -> dict:
    """按 category 分组记忆"""
    grouped = {
        "profiles": [],
        "events": [],
        "activities": [],
        "preferences": [],
        "other": []
    }
    
    for entry in memory_items:
        entry_dict = entry if isinstance(entry, dict) else {}
        
        # 解析嵌套的 memory 对象
        memory_obj = entry_dict.get("memory", entry_dict)
        if not isinstance(memory_obj, dict):
            memory_obj = entry_dict
        
        category = memory_obj.get("category", "other")
        content = memory_obj.get("content", "") or memory_obj.get("memory", "")
        timestamp = memory_obj.get("happened_at") or memory_obj.get("created_at", "")
        
        if not content:
            continue
        
        if category in grouped:
            grouped[category].append((timestamp, content))
        else:
            grouped["other"].append((timestamp, content))
    
    return grouped


def format_grouped_output(grouped: dict) -> str:
    """格式化分组输出"""
    output = []
    for category, title in CATEGORY_TITLES.items():
        items = grouped.get(category, [])
        if not items:
            continue
        
        output.append(f"## {title}")
        
        # 按时间倒序排列
        items.sort(key=lambda x: x[0] or "", reverse=True)
        
        for ts, content in items[:5]:
            if category in ("events", "activities") and ts:
                try:
                    dt = ts.split(".")[0]
                    formatted_time = dt.replace("T", " ").split(" ")[0]
                except:
                    formatted_time = ts
                output.append(f"- [{formatted_time}] {content}")
            else:
                output.append(f"- {content}")
    
    # 处理 other 分类
    other_items = grouped.get("other", [])
    if other_items:
        output.append("## 其他")
        other_items.sort(key=lambda x: x[0] or "", reverse=True)
        for ts, content in other_items[:5]:
            output.append(f"- {content}")

    return "\n".join(output)


def get_agent_id_for_save(context: dict, default_agent_id: str) -> str:
    """获取 save_memory 使用的 agent_id"""
    if context and context.get("agent_id"):
        return context["agent_id"]
    return default_agent_id


# ==================== 测试用例 ====================

class TestParseMemoryItems(unittest.TestCase):
    """测试 parse_memory_items 函数"""

    def test_parse_related_memories_format(self):
        """测试解析 related_memories 格式（新 API）"""
        data = {
            "related_memories": [
                {"memory": {"category": "profiles", "content": "喜欢运动"}}
            ],
            "total_found": 1
        }
        
        result = parse_memory_items(data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["memory"]["content"], "喜欢运动")

    def test_parse_memory_items_format(self):
        """测试解析 memory_items 格式（旧 API）"""
        data = {
            "memory_items": [
                {"category": "activities", "content": "打网球"}
            ]
        }
        
        result = parse_memory_items(data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "打网球")

    def test_parse_list_format(self):
        """测试解析列表格式"""
        data = [{"content": "测试内容"}]
        
        result = parse_memory_items(data)
        
        self.assertEqual(len(result), 1)

    def test_parse_empty_returns_empty_list(self):
        """测试空数据返回空列表"""
        data = {"related_memories": []}
        
        result = parse_memory_items(data)
        
        self.assertEqual(result, [])


class TestGroupMemoriesByCategory(unittest.TestCase):
    """测试 group_memories_by_category 函数"""

    def test_group_nested_memory_object(self):
        """测试分组嵌套的 memory 对象（新 API 格式）"""
        memory_items = [
            {
                "memory": {
                    "category": "profiles",
                    "content": "喜欢运动",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "similarity_score": 0.95
            }
        ]
        
        result = group_memories_by_category(memory_items)
        
        self.assertEqual(len(result["profiles"]), 1)
        self.assertEqual(result["profiles"][0][1], "喜欢运动")

    def test_group_flat_memory_object(self):
        """测试分组扁平的 memory 对象（旧 API 格式）"""
        memory_items = [
            {
                "category": "activities",
                "content": "打网球",
                "happened_at": "2024-12-10T14:00:00Z"
            }
        ]
        
        result = group_memories_by_category(memory_items)
        
        self.assertEqual(len(result["activities"]), 1)
        self.assertEqual(result["activities"][0][1], "打网球")

    def test_group_multiple_categories(self):
        """测试多种类型的记忆正确分组"""
        memory_items = [
            {"memory": {"category": "profiles", "content": "喜欢运动"}},
            {"memory": {"category": "events", "content": "昨天看电影"}},
            {"memory": {"category": "preferences", "content": "喜欢安静"}}
        ]
        
        result = group_memories_by_category(memory_items)
        
        self.assertEqual(len(result["profiles"]), 1)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(len(result["preferences"]), 1)

    def test_unknown_category_goes_to_other(self):
        """测试未知类型归入 other"""
        memory_items = [
            {"memory": {"category": "unknown_type", "content": "某内容"}}
        ]
        
        result = group_memories_by_category(memory_items)
        
        self.assertEqual(len(result["other"]), 1)

    def test_empty_content_skipped(self):
        """测试空内容被跳过"""
        memory_items = [
            {"memory": {"category": "profiles", "content": ""}}
        ]
        
        result = group_memories_by_category(memory_items)
        
        self.assertEqual(len(result["profiles"]), 0)


class TestFormatGroupedOutput(unittest.TestCase):
    """测试 format_grouped_output 函数"""

    def test_format_profiles_without_timestamp(self):
        """测试 profiles 不带时间戳"""
        grouped = {
            "profiles": [("2024-01-01T00:00:00Z", "素食主义者")],
            "events": [],
            "activities": [],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertIn("## 用户画像", result)
        self.assertIn("- 素食主义者", result)
        self.assertNotIn("[2024-01-01]", result)

    def test_format_events_with_timestamp(self):
        """测试 events 带时间戳"""
        grouped = {
            "profiles": [],
            "events": [("2024-12-10T20:00:00Z", "看电影")],
            "activities": [],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertIn("## 近期事件", result)
        self.assertIn("[2024-12-10]", result)
        self.assertIn("看电影", result)

    def test_format_activities_with_timestamp(self):
        """测试 activities 带时间戳"""
        grouped = {
            "profiles": [],
            "events": [],
            "activities": [("2024-12-10T14:00:00Z", "打网球")],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertIn("## 近期活动", result)
        self.assertIn("[2024-12-10]", result)
        self.assertIn("打网球", result)

    def test_format_preferences_without_timestamp(self):
        """测试 preferences 不带时间戳"""
        grouped = {
            "profiles": [],
            "events": [],
            "activities": [],
            "preferences": [("2024-01-01T00:00:00Z", "喜欢安静")],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertIn("## 用户偏好", result)
        self.assertIn("- 喜欢安静", result)
        self.assertNotIn("[2024-01-01]", result)

    def test_format_empty_groups_skipped(self):
        """测试空分组被跳过"""
        grouped = {
            "profiles": [("", "有内容")],
            "events": [],
            "activities": [],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertIn("## 用户画像", result)
        self.assertNotIn("## 近期事件", result)
        self.assertNotIn("## 近期活动", result)

    def test_format_max_5_items_per_category(self):
        """测试每类最多 5 条"""
        grouped = {
            "profiles": [(f"2024-01-0{i}T00:00:00Z", f"内容{i}") for i in range(1, 8)],
            "events": [],
            "activities": [],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        # 应该只有 5 条
        self.assertEqual(result.count("- 内容"), 5)

    def test_format_all_empty_returns_empty_string(self):
        """测试全空返回空字符串"""
        grouped = {
            "profiles": [],
            "events": [],
            "activities": [],
            "preferences": [],
            "other": []
        }
        
        result = format_grouped_output(grouped)
        
        self.assertEqual(result, "")


class TestGetAgentIdForSave(unittest.TestCase):
    """测试 agent_id 获取逻辑"""

    def test_context_agent_id_takes_priority(self):
        """测试 context 中的 agent_id 优先"""
        context = {"agent_id": "context_agent"}
        default = "default_agent"
        
        result = get_agent_id_for_save(context, default)
        
        self.assertEqual(result, "context_agent")

    def test_fallback_to_default_when_context_empty(self):
        """测试 context 为空时使用默认值"""
        context = {}
        default = "default_agent"
        
        result = get_agent_id_for_save(context, default)
        
        self.assertEqual(result, "default_agent")

    def test_fallback_to_default_when_context_none(self):
        """测试 context 为 None 时使用默认值"""
        context = None
        default = "default_agent"
        
        result = get_agent_id_for_save(context, default)
        
        self.assertEqual(result, "default_agent")

    def test_fallback_when_agent_id_is_none_in_context(self):
        """测试 context.agent_id 为 None 时使用默认值"""
        context = {"agent_id": None}
        default = "default_agent"
        
        result = get_agent_id_for_save(context, default)
        
        self.assertEqual(result, "default_agent")


class TestIntegration(unittest.TestCase):
    """集成测试：完整流程"""

    def test_full_query_memory_flow(self):
        """测试完整的 query_memory 流程"""
        # 模拟 API 返回
        api_response = {
            "related_memories": [
                {
                    "memory": {
                        "category": "profiles",
                        "content": "喜欢打网球",
                        "created_at": "2024-01-15T10:30:00Z"
                    },
                    "similarity_score": 0.95
                },
                {
                    "memory": {
                        "category": "activities",
                        "content": "周末打了网球",
                        "happened_at": "2024-12-10T14:00:00Z"
                    },
                    "similarity_score": 0.85
                },
                {
                    "memory": {
                        "category": "preferences",
                        "content": "喜欢户外运动",
                        "created_at": "2024-01-01T00:00:00Z"
                    },
                    "similarity_score": 0.80
                }
            ],
            "total_found": 3
        }
        
        # 执行完整流程
        memory_items = parse_memory_items(api_response)
        grouped = group_memories_by_category(memory_items)
        result = format_grouped_output(grouped)
        
        # 验证输出
        self.assertIn("## 用户画像", result)
        self.assertIn("- 喜欢打网球", result)
        
        self.assertIn("## 近期活动", result)
        self.assertIn("[2024-12-10]", result)
        self.assertIn("周末打了网球", result)
        
        self.assertIn("## 用户偏好", result)
        self.assertIn("- 喜欢户外运动", result)

    def test_empty_response_returns_empty(self):
        """测试空响应返回空字符串"""
        api_response = {"related_memories": []}
        
        memory_items = parse_memory_items(api_response)
        grouped = group_memories_by_category(memory_items)
        result = format_grouped_output(grouped)
        
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
