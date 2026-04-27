import uuid
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime


class Message:
    def __init__(
        self,
        role: str,
        content: str = None,
        uniq_id: str = None,
        tool_calls=None,
        tool_call_id=None,
        is_temporary: bool = False,
    ):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.is_temporary = is_temporary  # 标记临时消息（如工具调用提醒）


class Dialogue:
    def __init__(self, config: dict = None, logger: logging.Logger = None):
        self.dialogue: List[Message] = []
        self.logger = logger

        # 从配置中读取最大历史轮数，默认为 10 轮
        if config:
            self.max_history_turns = config.get("max_history_turns", 6)
        else:
            self.max_history_turns = 6

    def _log_debug(self, msg: str):
        if self.logger:
            self.logger.debug(msg)

    def put(self, message: Message):
        self.dialogue.append(message)

    def getMessages(self, m, dialogue):
        if m.tool_calls is not None:
            dialogue.append({"role": m.role, "tool_calls": m.tool_calls})
        elif m.role == "tool":
            dialogue.append(
                {
                    "role": m.role,
                    "tool_call_id": (
                        str(uuid.uuid4()) if m.tool_call_id is None else m.tool_call_id
                    ),
                    "content": m.content,
                }
            )
        else:
            dialogue.append({"role": m.role, "content": m.content})

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        # 直接调用get_llm_dialogue_with_memory，传入None作为memory_str
        # 这样确保说话人功能在所有调用路径下都生效
        return self.get_llm_dialogue_with_memory(None, None)

    def update_system_message(self, new_content: str):
        """更新或添加系统消息"""
        # 查找第一个系统消息
        system_msg = next((msg for msg in self.dialogue if msg.role == "system"), None)
        if system_msg:
            system_msg.content = new_content
        else:
            self.put(Message(role="system", content=new_content))

    def _group_messages_by_turns(self, messages: List[Message]) -> List[List[Message]]:
        """
        将消息按对话轮次分组
        """
        turns = []
        current_turn = []

        for msg in messages:
            if msg.role == "user":
                if current_turn:
                    turns.append(current_turn)
                current_turn = [msg]
            else:
                current_turn.append(msg)

        if current_turn:
            turns.append(current_turn)

        return turns

    def _ensure_tool_calls_complete(self, messages: List[Message]) -> List[Message]:
        """
        确保所有 tool_calls 都有对应的 tool 响应
        
        修复被打断导致的悬空 tool_calls，防止大模型 API 报 400 错误
        """
        pending_tool_calls = set()
        result = []

        for msg in messages:
            result.append(msg)

            # 记录 assistant 发出的 tool_calls ID
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    # 兼容字典和对象两种格式
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if tc_id:
                        pending_tool_calls.add(tc_id)

            # tool 响应核销对应的 ID
            elif msg.role == "tool" and msg.tool_call_id:
                pending_tool_calls.discard(msg.tool_call_id)

        # 为悬空的 tool_calls 补齐占位响应
        for missing_id in pending_tool_calls:
            dummy_tool_msg = Message(
                role="tool",
                content='{"status": "interrupted", "message": "动作已取消/被打断"}',
                tool_call_id=missing_id
            )
            result.append(dummy_tool_msg)
            self._log_debug(f"已为悬空的 tool_call({missing_id}) 自动补齐占位响应")

        return result

    def get_llm_dialogue_with_memory(
        self,
        memory_str: str = None,
        voiceprint_config: dict = None
    ) -> List[Dict[str, str]]:
        # 构建对话
        dialogue = []

        # 添加系统提示和记忆
        system_message = next(
            (msg for msg in self.dialogue if msg.role == "system"), None
        )

        if system_message:
            # 基础系统提示
            enhanced_system_prompt = system_message.content
            # 替换时间占位符
            enhanced_system_prompt = enhanced_system_prompt.replace(
                "{{current_time}}", datetime.now().strftime("%H:%M")
            )

            # 添加说话人个性化描述
            if voiceprint_config:
                try:
                    speakers = voiceprint_config.get("speakers", [])
                    if speakers:
                        enhanced_system_prompt += "\n\n<speakers_info>"
                        for speaker_str in speakers:
                            try:
                                parts = speaker_str.split(",", 2)
                                if len(parts) >= 2:
                                    name = parts[1].strip()
                                    description = parts[2].strip() if len(parts) >= 3 else ""
                                    enhanced_system_prompt += f"\n- {name}：{description}"
                            except Exception:
                                pass
                        enhanced_system_prompt += "\n\n</speakers_info>"
                except Exception:
                    pass

            # 注入记忆内容
            if memory_str is not None:
                enhanced_system_prompt = re.sub(
                    r"<memory>.*?</memory>",
                    f"<memory>\n{memory_str}\n</memory>",
                    enhanced_system_prompt,
                    flags=re.DOTALL,
                )

            dialogue.append({"role": "system", "content": enhanced_system_prompt})

        # 获取非系统消息
        non_system_messages = [m for m in self.dialogue if m.role != "system"]

        if not non_system_messages:
            return dialogue

        # 找到最后一个 user 的位置（当前轮次的起点）
        last_user_idx = -1
        for i in range(len(non_system_messages) - 1, -1, -1):
            if non_system_messages[i].role == "user":
                last_user_idx = i
                break

        # 如果没有 user 消息，直接返回
        if last_user_idx == -1:
            for m in non_system_messages:
                self.getMessages(m, dialogue)
            return dialogue

        # 历史轮次：截断并确保完整性
        history_messages = non_system_messages[:last_user_idx]
        # 当前轮次：原封不动保留
        current_turn_messages = non_system_messages[last_user_idx:]

        # 处理历史轮次
        if history_messages:
            history_turns = self._group_messages_by_turns(history_messages)
            max_history = self.max_history_turns - 1
            if max_history < 1:
                max_history = 1

            if len(history_turns) > max_history:
                history_turns = history_turns[-max_history:]

            for turn in history_turns:
                complete_turn = self._ensure_tool_calls_complete(turn)
                for m in complete_turn:
                    self.getMessages(m, dialogue)

        # 当前轮次原封不动保留
        for m in current_turn_messages:
            self.getMessages(m, dialogue)

        return dialogue