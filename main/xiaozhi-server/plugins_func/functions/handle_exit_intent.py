import requests
from config.settings import XIAOZHI_BASE_URL, XIAOZHI_USER_TOKEN, DEFAULT_AGENT_ID
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

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
    # Processar intenção de encerramento da conversa
    try:
        if say_goodbye is None:
            say_goodbye = "Até logo! Tenha um ótimo dia!"
        if not conn.close_after_chat:
            conn.close_after_chat = True

        logger.bind(tag=TAG).info(
            f"Intenção de encerramento processada: {say_goodbye}"
        )
        
        

        # SUCCESS
        # Vamos montar uma requisição para o servidor JAVA 
        # PUT para o /agent/:agent_id/
        # Body 
        # {
        #     "summaryMemory": "eai "
        # } 
        # --- REQUISIÇÃO PUT PARA O SERVIDOR JAVA ---
        agent_id = DEFAULT_AGENT_ID
        user_token = XIAOZHI_USER_TOKEN
        base_url = XIAOZHI_BASE_URL

        headers = {"Content-Type": "application/json"}
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}" if not user_token.startswith("Bearer ") else user_token

        update_agent_url = f"{base_url}/agent/{agent_id}"
        payload = {
            "summaryMemory": ""  # Adicione/substitua pelo resumo real caso tenha essa variável
        }

        logger.bind(tag=TAG).info(f"[ExitIntent] Enviando PUT para {update_agent_url} com payload: {payload}")

        # Requisição PUT
        res = requests.put(update_agent_url, json=payload, headers=headers, timeout=5)
        logger.bind(tag=TAG).info(f"[ExitIntent] Resposta do Java ({res.status_code}): {res.text}")
        
        return ActionResponse(
            action=Action.RESPONSE, result="Intenção de encerramento processada", response=say_goodbye,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(
            f"Erro ao processar intenção de encerramento: {e}"
        )

        return ActionResponse(
            action=Action.NONE, result="Falha ao processar intenção de encerramento", response="",
        )

