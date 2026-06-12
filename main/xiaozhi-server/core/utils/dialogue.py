import uuid
import re
from typing import List, Dict
from datetime import datetime


class Message:
    def __init__(
            self,
            role: str,
            content: str = None,
            uniq_id: str = None,
            tool_calls=None,
            tool_call_id=None,
            is_temporary=False,
    ):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.is_temporary = is_temporary  # 标记临时消息（如工具调用提醒）


class Dialogue:
    def __init__(self):
        self.dialogue: List[Message] = []
        # 获取当前时间
        self.current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    def _ensure_tool_calls_complete(self, messages: List[Message]) -> List[Message]:
        """
        确保所有 tool_calls 都有对应的 tool 响应
        修复被打断导致的悬空 tool_calls，防止大模型 API 报 400 错误
        """
        pending_tool_calls = set()
        result = []

        for msg in messages:
            result.append(msg)

            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if tc_id:
                        pending_tool_calls.add(tc_id)

            elif msg.role == "tool" and msg.tool_call_id:
                pending_tool_calls.discard(msg.tool_call_id)

        for missing_id in pending_tool_calls:
            dummy_tool_msg = Message(
                role="tool",
                content='{"status": "interrupted", "message": "动作已取消/被打断"}',
                tool_call_id=missing_id
            )
            result.append(dummy_tool_msg)

        return result

    def get_llm_dialogue_with_memory(
            self, memory_str: str = None, voiceprint_config: dict = None
    ) -> List[Dict[str, str]]:
        # 构建对话
        dialogue = []

        # 添加系统提示和记忆
        system_message = next(
            (msg for msg in self.dialogue if msg.role == "system"), None
        )

        if system_message:
            # 以 <context> 为分界点，拆分静态 system prompt 和动态上下文
            # 静态部分（规则、身份等）保持不变，可命中前缀缓存
            # 动态部分（时间、天气、记忆等）作为第二条 system 消息，保持 system 权威性
            full_prompt = system_message.content
            context_match = re.search(r"<context>", full_prompt)
            if context_match:
                static_part = full_prompt[:context_match.start()]
                dynamic_part = full_prompt[context_match.start():]
            else:
                static_part = full_prompt
                dynamic_part = ""

            # 第一段：静态 system prompt（前缀缓存可命中）
            dialogue.append({"role": "system", "content": static_part})

        # 第二段：few-shot 示例（会话内不变，也是缓存前缀的一部分，可命中缓存）
        non_system_messages = [m for m in self.dialogue if m.role != "system"]
        fewshot_messages = [m for m in non_system_messages if m.is_temporary]
        complete_fewshot = self._ensure_tool_calls_complete(fewshot_messages)
        for m in complete_fewshot:
            self.getMessages(m, dialogue)

        # 第三段 + 第四段：将动态上下文拆分为半稳定和实时两部分
        # 半稳定部分（system 角色）：日期、农历、位置、天气、dynamic_context — 同一天内不变
        # 实时部分（user 角色）：当前时间、记忆、说话人 — 每次调用都可能变
        # 拆分目的：半稳定的 system 消息可以被缓存前缀覆盖，实时变化不影响缓存
        if system_message and dynamic_part:
            # 构建实时变化内容（每次调用都不同）
            realtime_parts = []
            current_time = datetime.now().strftime("%H:%M")
            realtime_parts.append(f"当前时间：{current_time}")

            # 填充记忆到实时部分
            if memory_str is not None:
                realtime_parts.append(f"<memory>\n{memory_str}\n</memory>")

            # 追加说话人信息到实时部分
            try:
                speakers = voiceprint_config.get("speakers", [])
                if speakers:
                    speakers_text = "<speakers_info>"
                    for speaker_str in speakers:
                        try:
                            parts = speaker_str.split(",", 2)
                            if len(parts) >= 2:
                                name = parts[1].strip()
                                description = (
                                    parts[2].strip() if len(parts) >= 3 else ""
                                )
                                speakers_text += f"\n- {name}：{description}"
                        except:
                            pass
                    speakers_text += "\n</speakers_info>"
                    realtime_parts.append(speakers_text)
            except:
                pass

            # 从 dynamic_part 中移除已提取到实时部分的占位符
            # 注意：模板中 {{current_time}} 已被 prompt_manager 渲染为实际时间值
            # 移除当前时间行（当前时间已移到实时 user 消息）
            semi_stable_part = re.sub(
                r"- 当前时间：[^\n]+\n?", "", dynamic_part
            )
            # 移除 <memory> 块（记忆已移到实时 user 消息）
            semi_stable_part = re.sub(
                r"<memory>.*?</memory>", "", semi_stable_part, flags=re.DOTALL
            )
            # 清理多余空行
            semi_stable_part = re.sub(r"\n{3,}", "\n\n", semi_stable_part).strip()

            # 第三段：半稳定 system prompt（日期、农历、位置、天气等）
            if semi_stable_part:
                dialogue.append({"role": "system", "content": semi_stable_part})

            # 第四段：实时变化内容（user 角色，不影响缓存前缀）
            if realtime_parts:
                dialogue.append({"role": "user", "content": "\n".join(realtime_parts)})

        # 第五段：实际对话历史（不含 few-shot）
        actual_messages = [m for m in non_system_messages if not m.is_temporary]
        complete_actual = self._ensure_tool_calls_complete(actual_messages)
        for m in complete_actual:
            self.getMessages(m, dialogue)

        return dialogue
