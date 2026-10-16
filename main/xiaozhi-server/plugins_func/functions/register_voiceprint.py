from typing import TYPE_CHECKING, Optional
import logging
import traceback
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from config.manage_api_client import (
    get_agent_chat_history_system,
    register_voiceprint_system,
)
from config.settings import DEFAULT_AGENT_ID

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
async def register_voiceprint(conn: "ConnectionHandler", speaker_id: Optional[str] = None):
    try:
        agent_id = getattr(conn, "agent_id", None) or DEFAULT_AGENT_ID

        # Buscar histórico recente de áudios via helper do ManageApiClient
        logger.bind(tag=TAG).info(f"[Voiceprint] Buscando histórico para o agente {agent_id}")
        audio_list = await get_agent_chat_history_system(agent_id)

        if audio_list is None:
            return ActionResponse(
                action=Action.NONE,
                result="Erro na API ao buscar histórico",
                response="Não consegui obter o histórico recente para cadastrar sua voz."
            )

        if not audio_list:
            logger.bind(tag=TAG).warning("[Voiceprint] Histórico de áudios retornado está vazio.")
            return ActionResponse(
                action=Action.NONE,
                result="Nenhum áudio encontrado no histórico do agente",
                response="Não encontrei nenhum registro de voz recente no histórico."
            )

        # Evita registrar se for apenas pergunta de identidade
        user_text = audio_list[0].get("content", "").lower()
        perguntas_identidade = ["quem sou", "me diga quem", "qual é o meu nome", "qual meu nome"]

        if any(p in user_text for p in perguntas_identidade):
            logger.bind(tag=TAG).info(f"[Voiceprint] Interceptado: Pergunta de identidade ('{user_text}'). Cancelando registro.")
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

        # Registrar biometria de voz no backend Java
        logger.bind(tag=TAG).info(f"[Voiceprint] Registrando biometria para {speaker_id}")
        res = await register_voiceprint_system(agent_id, audio_id, speaker_id)

        if res is not None:
            return ActionResponse(
                action=Action.RESPONSE,
                result=f"Voiceprint de {speaker_id} registrado com sucesso",
                response=f"Pronto! Cadastrei a voz de {speaker_id} no sistema."
            )
        else:
            return ActionResponse(
                action=Action.NONE,
                result="Falha no salvamento do Voiceprint",
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