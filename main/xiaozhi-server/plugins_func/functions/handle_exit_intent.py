import threading
import asyncio
from typing import TYPE_CHECKING
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.settings import DEFAULT_AGENT_ID
from config.manage_api_client import clear_agent_memory

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

handle_exit_intent_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_exit_intent",
        "description": "当用户想结束对话或需要退出系统时调用",
        "parameters": {
            "type": "object",
            "properties": {
                "say_goodbye": {
                    "type": "string",
                    "description": "和用户友好结束对话的告别语",
                }
            },
            "required": ["say_goodbye"],
        },
    },
}


@register_function(
    "handle_exit_intent", handle_exit_intent_function_desc, ToolType.SYSTEM_CTL
)
def handle_exit_intent(conn: "ConnectionHandler", say_goodbye: str | None = None):
    try:
        if say_goodbye is None:
            say_goodbye = "Até logo!"

        conn.close_after_chat = True
        agent_id = getattr(conn, "agent_id", DEFAULT_AGENT_ID)

        # Limpa a memória no Java em background via ManageApiClient
        def clear_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(clear_agent_memory(agent_id))
            finally:
                loop.close()

        threading.Thread(target=clear_task, daemon=True).start()

        # Limpa o histórico em memória local para não regravar nada na desconexão
        if hasattr(conn, "dialogue") and conn.dialogue:
            conn.dialogue.dialogue.clear()

        return ActionResponse(
            action=Action.RESPONSE,
            result="Intenção de encerramento processada",
            response=say_goodbye,
        )

    except Exception as e:
        return ActionResponse(
            action=Action.NONE,
            result=f"Falha ao processar intenção de encerramento: {e}",
            response="",
        )