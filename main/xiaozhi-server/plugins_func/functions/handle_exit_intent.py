from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging

from typing import Optional

TAG = __name__
logger = setup_logging()

handle_exit_intent_function_desc = {
    "type": "function",
    "function": {
        "name": "say_goodbye",
        "description": "Called when user wants to end conversation or exit system",
        "parameters": {
            "type": "object",
            "properties": {
                "say_goodbye": {
                    "type": "string",
                    "description": "Farewell message to end conversation friendlily",
                }
            },
            "required": ["say_goodbye"],
        },
    },
}


@register_function(
    "say_goodbye", handle_exit_intent_function_desc, ToolType.SYSTEM_CTL
)
def handle_exit_intent(conn, say_goodbye: Optional[str] = None, **kwargs):
    # Handle exit intent
    try:
        if say_goodbye is None:
            say_goodbye = "Goodbye, have a nice day!"
        conn.close_after_chat = True
        logger.bind(tag=TAG).info(f"Exit intent handled:{say_goodbye}")
        return ActionResponse(
            action=Action.RESPONSE, result="Exit intent handled", response=say_goodbye
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error handling exit intent: {e}")
        return ActionResponse(
            action=Action.NONE, result="Failed to handle exit intent", response=""
        )
