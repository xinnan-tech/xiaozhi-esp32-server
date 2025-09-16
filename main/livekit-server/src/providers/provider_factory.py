import livekit.plugins.groq as groq
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins.turn_detector.english import EnglishModel

class ProviderFactory:
    """Factory class for creating AI service providers"""

    @staticmethod
    def create_llm(config):
        """Create LLM provider based on configuration"""
        return groq.LLM(model=config['llm_model'])

    @staticmethod
    def create_stt(config):
        """Create Speech-to-Text provider based on configuration"""
        return groq.STT(
            model=config['stt_model'],
            language=config['stt_language']
        )

    @staticmethod
    def create_tts(config):
        """Create Text-to-Speech provider based on configuration"""
        return groq.TTS(
            model=config['tts_model'],
            voice=config['tts_voice']
        )

    @staticmethod
    def create_vad():
        """Create Voice Activity Detection provider"""
        return silero.VAD.load()

    @staticmethod
    def create_turn_detection():
        """Create turn detection model"""
       # return MultilingualModel()
        return  EnglishModel()