from typing import TYPE_CHECKING, Optional
import requests
import logging
import traceback
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from config.settings import XIAOZHI_BASE_URL, XIAOZHI_USER_TOKEN, DEFAULT_AGENT_ID

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

register_voiceprint_function_desc = {
    "type": "function",
    "function": {
        "name": "register_voiceprint",
        "description": "ONLY call this function when the user explicitly commands to save or register their name (e.g., 'meu nome é X', 'salve meu nome como X'). DO NOT call this if the user asks 'who am I' or asks a question.",
        "parameters": {
            "type": "object",
            "properties": {
                "speaker_id": {
                    "type": "string",
                    "description": "Nome ou ID do usuário a ser cadastrado (ex: Jordan)",
                }
            },
            "required": ["speaker_id"],
        },
    },
}


@register_function(
    "register_voiceprint", register_voiceprint_function_desc, ToolType.SYSTEM_CTL
)
def register_voiceprint(conn: "ConnectionHandler", speaker_id: Optional[str] = None):
    try:
        # Configuração do Agent ID e Token de Autenticação ainda hardcoded
        # TODO: Implementar a obtenção dinâmica do token de autenticação, aparentemente o agent_id não muda

        agent_id = DEFAULT_AGENT_ID
        user_token = XIAOZHI_USER_TOKEN
        base_url = XIAOZHI_BASE_URL
        
        headers = {"Content-Type": "application/json"}
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}" if not user_token.startswith("Bearer ") else user_token

        # Consultar o histórico de áudios
        history_url = f"{base_url}/agent/{agent_id}/chat-history/user"
        logger.bind(tag=TAG).info(f"[Voiceprint] Buscando histórico em: {history_url}")
        
        history_res = requests.get(history_url, headers=headers, timeout=5)
        logger.bind(tag=TAG).info(f"[Voiceprint] Resposta do histórico ({history_res.status_code}): {history_res.text}")

        if history_res.status_code != 200:
            return ActionResponse(
                action=Action.NONE,
                result=f"Erro na API de histórico: status {history_res.status_code}",
                response="Não consegui obter o histórico recente para cadastrar sua voz."
            )

        history_data = history_res.json()
        audio_list = history_data.get("data", [])

        if not audio_list:
            logger.bind(tag=TAG).warning("[Voiceprint] A API retornou uma lista de áudios vazia (data: []).")
            return ActionResponse(
                action=Action.NONE,
                result="Nenhum áudio encontrado no histórico do agente",
                response="Não encontrei nenhum registro de voz recente no histórico."
            )

        # evita registrar a voz se o usuário apenas perguntou "quem sou eu" ou algo similar
        user_text = audio_list[0].get("content", "").lower()
        perguntas_identidade = ["quem sou", "me diga quem", "qual é o meu nome", "qual meu nome"]

        if any(p in user_text for p in perguntas_identidade):
            logger.bind(tag=TAG).info(f"[Voiceprint] Interceptado: Usuário apenas perguntou a identidade ('{user_text}'). Cancelando registro.")
            return ActionResponse(
                action=Action.NONE,
                result="Ignorado: O usuário apenas perguntou quem ele é.",
                response=f"Eu sei quem você é! Você é o {speaker_id}."
            )

        # Áudio mais recente
        latest_audio = audio_list[0]
        audio_id = latest_audio.get("audioId")

        if not audio_id:
            logger.bind(tag=TAG).error(f"[Voiceprint] Item do histórico sem audioId: {latest_audio}")
            return ActionResponse(
                action=Action.NONE,
                result="audioId ausente no item mais recente",
                response="Não foi possível identificar o código do seu último áudio."
            )

        logger.bind(tag=TAG).info(f"[Voiceprint] Áudio selecionado: audioId={audio_id}, texto='{latest_audio.get('content')}'")

        #  Enviar requisição de salvamento do Voiceprint
        register_url = f"{base_url}/agent/voice-print"
        payload = {
            "agentId": agent_id,
            "audioId": audio_id,
            "introduce": speaker_id,
            "sourceName": speaker_id
        }

        logger.bind(tag=TAG).info(f"[Voiceprint] Enviando cadastro: {payload}")
        register_res = requests.post(register_url, json=payload, headers=headers, timeout=5)
        logger.bind(tag=TAG).info(f"[Voiceprint] Resposta do cadastro ({register_res.status_code}): {register_res.text}")

        res_json = register_res.json() if register_res.status_code == 200 else {}
        code = res_json.get("code")

        # Sucesso
        if register_res.status_code == 200 and code == 0:
            return ActionResponse(
                action=Action.RESPONSE,
                result=f"Voiceprint de {speaker_id} registrado com sucesso",
                response=f"Pronto! Cadastrei a voz de {speaker_id} no sistema."
            )
        # Tratamento da voz já cadastrada
        elif code == 10080:
            logger.bind(tag=TAG).info(f"[Voiceprint] Voz já cadastrada anteriormente como {speaker_id}.")
            return ActionResponse(
                action=Action.RESPONSE,
                result=f"Voz já cadastrada para {speaker_id}",
                response=f"Sua voz já está cadastrada no sistema como {speaker_id}."
            )
        # Outros erros
        else:
            return ActionResponse(
                action=Action.NONE,
                result=f"Falha no salvamento: {register_res.text}",
                response="Ocorreu um erro no servidor ao tentar salvar sua voz."
            )

    except Exception as e:
        logger.bind(tag=TAG).error(f"[Voiceprint] Exceção: {e}")
        logger.bind(tag=TAG).error(traceback.format_exc())
        return ActionResponse(
            action=Action.NONE,
            result=f"Exceção: {e}",
            response="Tive um problema ao processar seu cadastro de voz."
        )