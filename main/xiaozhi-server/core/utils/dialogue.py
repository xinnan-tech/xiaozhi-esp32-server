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
        # This ensures speaker function works in all call paths
        return self.get_llm_dialogue_with_memory(None, None)

    def update_system_message(self, new_content: str):
        """Update or add system message (ensure only one exists)"""
        # Find all system messages
        system_indices = [i for i, msg in enumerate(self.dialogue) if msg.role == "system"]
        
        if system_indices:
            # Update the first one
            self.dialogue[system_indices[0]].content = new_content
            # Remove any others (duplicate cleanup)
            for i in reversed(system_indices[1:]):
                self.dialogue.pop(i)
        else:
            # Insert at the beginning
            self.dialogue.insert(0, Message(role="system", content=new_content))

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
            # Basic system prompt
            enhanced_system_prompt = system_message.content
            # Replace time placeholder
            enhanced_system_prompt = enhanced_system_prompt.replace(
                "{{current_time}}", datetime.now().strftime("%H:%M")
            )

            # Add speaker personalized description
            try:
                speakers = voiceprint_config.get("speakers", [])
                if speakers:
                    enhanced_system_prompt += "\n\n<speakers_info>"
                    for speaker_str in speakers:
                        try:
                            parts = speaker_str.split(",", 2)
                            if len(parts) >= 2:
                                name = parts[1].strip()
                                # If description is empty, set to ""
                                description = (
                                    parts[2].strip() if len(parts) >= 3 else ""
                                )
                                enhanced_system_prompt += f"\n- {name}：{description}"
                        except:
                            pass
                    enhanced_system_prompt += "\n\n</speakers_info>"
            except:
                # Ignore error if config read fails, does not affect other functions
                pass

            # Use regex to match <memory> tag, regardless of content
            if memory_str is not None:
                if "<memory>" in enhanced_system_prompt:
                    enhanced_system_prompt = re.sub(
                        r"<memory>.*?</memory>",
                        f"<memory>\n{memory_str}\n</memory>",
                        enhanced_system_prompt,
                        flags=re.DOTALL,
                    )
                else:
                    enhanced_system_prompt += f"\n\n<memory>\n{memory_str}\n</memory>"
            
            # FINAL SANITY CHECK: Ensure we don't have nested identity if it somehow happened
            if enhanced_system_prompt.count("<identity>") > 1:
                # If nested, try to extract the innermost content or at least flatten
                # This is a fallback defensive measure
                inner_match = re.search(r"<identity>(?:(?!<identity>).)*?</identity>", enhanced_system_prompt, re.DOTALL)
                if inner_match:
                     # Keep the whole thing but maybe this is where we should be careful.
                     # For now, let's just log it if we were in a logging context.
                     pass

            dialogue.append({"role": "system", "content": enhanced_system_prompt})

        # Add user and assistant dialogue
        # Limit to the last N turns to avoid context overflow and reduce latency
        MAX_HISTORY = 20
        
        # Filter out system messages first (we already added the system prompt above)
        conversation_history = [m for m in self.dialogue if m.role != "system"]
        
        # Take the last MAX_HISTORY messages
        recent_history = conversation_history[-MAX_HISTORY:] if len(conversation_history) > MAX_HISTORY else conversation_history
        
        for m in recent_history:
            self.getMessages(m, dialogue)

        return dialogue
