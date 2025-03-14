import uuid
from typing import List, Dict
from datetime import datetime


class Message:
    def __init__(self, role: str, content: str = None, uniq_id: str = None):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content


class Dialogue:
    def __init__(self):
        self.dialogue: List[Message] = []
        # 获取当前时间
        self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def put(self, message: Message):
        self.dialogue.append(message)

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        dialogue = []
        for m in self.dialogue:
            dialogue.append({"role": m.role, "content": m.content})
        return dialogue

    def get_llm_dialogue_with_memory(self, memory_str: str = None) -> List[Dict[str, str]]:
        if memory_str is None or len(memory_str) == 0:
            return self.get_llm_dialogue()
        
        # 构建带记忆的对话
        dialogue = []
        
        # 添加系统提示和记忆
        system_message = next(
            (msg for msg in self.dialogue if msg.role == "system"), None
        )


        if system_message:
            enhanced_system_prompt = (
                f"{system_message.content}\n\n"
                f"相关记忆：\n{memory_str}"
            )
            dialogue.append({"role": "system", "content": enhanced_system_prompt})

        # 添加用户和助手的对话
        for msg in self.dialogue:
            if msg.role != "system":  # 跳过原始的系统消息
                dialogue.append({"role": msg.role, "content": msg.content})

        return dialogue
