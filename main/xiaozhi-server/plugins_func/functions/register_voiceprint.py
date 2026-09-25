from typing import TYPE_CHECKING, Optional
import requests
import glob
import os
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

register_voiceprint_function_desc = {
    "type": "function",
    "function": {
        "name": "register_voiceprint",
        "description": "Register the user's voiceprint for future identification",
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
        audio_path = getattr(conn, "last_audio_file", None)
        
        if not audio_path and hasattr(conn, "session_id"):
            session_files = sorted(glob.glob(f"tmp/*{conn.session_id}*.wav"), key=os.path.getmtime)
            if session_files:
                audio_path = session_files[-1]

        if not audio_path or not os.path.exists(audio_path):
            return ActionResponse(
                action=Action.NONE,
                result="Audio file not found for voice registration",
                response="I couldn't find the audio file to register your voice. Please make sure to record your voice first."
            )

        with open(audio_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_path), f, 'audio/wav')}
            payload = {'speaker_id': speaker_id}
            
            response = requests.post(
                'http://192.168.1.178:8005/voiceprint/register',
                data=payload,
                files=files,
                timeout=5
            )

        if response.status_code == 200:
            return ActionResponse(
                action=Action.NONE,
                result=f"Voiceprint de {speaker_id} registrado com sucesso",
                response=f"Pronto! Cadastrei a voz de {speaker_id} no sistema."
            )
        else:
            logger.bind(tag=TAG).error(f"Erro API Voiceprint: {response.status_code} - {response.text}")
            return ActionResponse(
                action=Action.NONE,
                result=f"Erro status {response.status_code}",
                response="Ocorreu um erro no servidor de voz ao tentar salvar."
            )

    except Exception as e:
        logger.bind(tag=TAG).error(f"Erro ao registrar a impressão de voz: {e}")
        return ActionResponse(
            action=Action.NONE,
            result=f"Exceção: {e}",
            response="Tive um problema ao processar seu cadastro de voz."
        )