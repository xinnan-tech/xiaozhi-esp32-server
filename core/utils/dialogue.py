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

    def get_llm_dialogue_with_memory(self, memory_data:str) -> List[Dict[str, str]]:
        dialogue = []            

        for m in self.dialogue:
            if m.role == "system" and len(memory_data.strip()) > 0:
                content = f"{m.content}\n\n你还保留着一些长期的记忆，这有助于让你的对话更加丰富和连贯：\n<start>{memory_data}</end>"
            else:
                content = m.content
            dialogue.append({"role": m.role, "content": content})
        
        return dialogue

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        dialogue = []
        for m in self.dialogue:
            dialogue.append({"role": m.role, "content": m.content})
        return dialogue
