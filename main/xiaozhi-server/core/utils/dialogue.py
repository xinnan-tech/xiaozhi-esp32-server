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
    ):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id


class Dialogue:
    def __init__(self):
        self.dialogue: List[Message] = []
        # Get current time
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
        # Directly call get_llm_dialogue_with_memory, passing None as memory_str
        # This ensures speaker functionality takes effect in all call paths
        return self.get_llm_dialogue_with_memory(None, None)

    def update_system_message(self, new_content: str):
        """Update or add system message"""
        # Find the first system message
        system_msg = next(
            (msg for msg in self.dialogue if msg.role == "system"), None)

        if system_msg:
            system_msg.content = new_content
        else:
            self.put(Message(role="system", content=new_content))

    def get_llm_dialogue_with_memory(
        self, memory_str: str = None, voiceprint_config: dict = None
    ) -> List[Dict[str, str]]:
        # Build dialogue
        dialogue = []

        # Add system prompt and memory
        system_message = next(
            (msg for msg in self.dialogue if msg.role == "system"), None
        )

        if system_message:
            # Base system prompt
            enhanced_system_prompt = system_message.content

            # Replace time placeholder
            enhanced_system_prompt = enhanced_system_prompt.replace(
                "{{current_time}}", datetime.now().strftime("%H:%M")
            )

            # Add speaker personalization description
            try:
                speakers = voiceprint_config.get("speakers", [])
                if speakers:
                    enhanced_system_prompt += "\n\n"
                    for speaker_str in speakers:
                        try:
                            parts = speaker_str.split(",", 2)
                            if len(parts) >= 2:
                                name = parts[1].strip()
                                # If description is empty, then ""
                                description = (
                                    parts[2].strip() if len(parts) >= 3 else ""
                                )
                                enhanced_system_prompt += f"\n- {name}: {description}"
                        except:
                            pass
                    enhanced_system_prompt += "\n\n"
            except:
                # Ignore errors when configuration reading fails, don't affect other functionality
                pass

            # Use regular expression to match <memory></memory> tags, regardless of content inside
            if memory_str is not None:
                enhanced_system_prompt = re.sub(
                    r"<memory>.*?</memory>",
                    f"\n<memory>{memory_str}</memory>\n",
                    enhanced_system_prompt,
                    flags=re.DOTALL,
                )

            dialogue.append(
                {"role": "system", "content": enhanced_system_prompt})

        # Add user and assistant dialogue
        for m in self.dialogue:
            if m.role != "system":  # Skip original system message
                self.getMessages(m, dialogue)

        return dialogue
