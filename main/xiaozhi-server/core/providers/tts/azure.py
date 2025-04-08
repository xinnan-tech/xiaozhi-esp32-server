import os
import uuid
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.subscription_key = config.get("subscription_key")
        self.region = config.get("region")
        self.voice_name = config.get("voice_name", "zh-CN-XiaoxiaoNeural")

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.subscription_key,
                region=self.region
            )
            speech_config.speech_synthesis_voice_name = self.voice_name
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            result = speech_synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.bind(tag=TAG).info(f"Azure TTS 合成已完成，文本: {text[:30]}...")
                return output_file
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_message = f"Azure TTS 合成已取消: {cancellation_details.reason}"
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    error_message += f" 错误详情: {cancellation_details.error_details}"
                logger.bind(tag=TAG).error(error_message)
                raise Exception(error_message)

        except Exception as e:
            logger.bind(tag=TAG).error(f"Azure TTS 错误: {e}")
            raise Exception(f"{TAG} 错误: {e}")