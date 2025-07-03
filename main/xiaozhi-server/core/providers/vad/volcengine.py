"""
This module provides a Voice Activity Detection (VAD) provider using the Volcengine service.

It combines basic VAD (like Silero) with semantic End-of-Utterance (EOU) detection
using embeddings to determine if a user has finished speaking.
"""
import openai

from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase
from core.utils.vad import create_instance

TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    """
    Implements a VAD provider based on Volcengine for semantic End-of-Utterance (EOU) detection.

    This class uses a base VAD model (e.g., Silero) for initial voice activity detection
    and leverages a Volcengine embedding model to determine if the user's speech
    constitutes a complete thought, allowing for more natural conversation flow.
    """

    def __init__(self, config: dict):
        """
        Initializes the Volcengine VAD provider.

        Args:
            config (dict): Configuration dictionary containing settings for the base VAD,
                         semantic detection, and Volcengine API credentials.
        """
        logger.bind(tag=TAG).info(f"init VAD_volcengine: config:{config}")
        config['model_dir'] = "models/snakers4_silero-vad"
        self.base_vad_model = create_instance("silero", config)
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")
        max_silence_duration_ms = config.get("max_silence_duration_ms", "3000")

        self.semantic_only = config.get("semantic_only", False)
        self.min_silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )
        self.max_silence_threshold_ms = (
            int(max_silence_duration_ms) if max_silence_duration_ms else 3000
        )
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.host = config.get("host","ai-gateway.vei.volces.com")

        self.base_url = f"https://{self.host}/v1"
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.cached_text = ""
        self.cached_embedding = None

    def is_vad(self, conn, data: bytes):
        """
        Performs basic Voice Activity Detection.

        If semantic_only is True, this check is bypassed. Otherwise, it delegates
        to the base VAD model.

        Args:
            conn: The connection object.
            data: The audio data chunk.

        Returns:
            bool: True if voice activity is detected, False otherwise.
        """
        if self.semantic_only:
            return True
        return self.base_vad_model.is_vad(conn, data)

    def is_eou(self, conn, text: str):
        """
        Determines if the end of an utterance (EOU) has been reached.

        This method combines semantic analysis from an embedding model with silence duration.
        The logic adjusts the EOU detection threshold based on how long the user has been silent.

        Args:
            conn: The connection object.
            text (str): The transcribed text so far.

        Returns:
            bool: True if the utterance is considered complete, False otherwise.
        """
        silence_duration = self.get_silence_duration(conn)
        logger.bind(tag=TAG).debug(f"silence_duration : {silence_duration}")
        # If text is empty, EOU is determined solely by silence duration.
        if not text or not text.strip():
            return silence_duration >= self.max_silence_threshold_ms

        # For semantic checks, we need the embedding.
        embedding, is_cached = self._get_embedding(text)
        is_stop = embedding[1] > 0.5
        if not is_cached or is_stop or silence_duration >= self.max_silence_threshold_ms:
            logger.bind(tag=TAG).info(f"EOU Result: text:{text} embedding:{embedding} semantic_stop:{is_stop} silence_duration:{silence_duration} cache:{is_cached}")
        if self.semantic_only:
            return is_stop

        if silence_duration <= self.min_silence_threshold_ms / 2:
            # If silence is short, be less likely to interrupt.
            return False
        elif silence_duration <= self.min_silence_threshold_ms:
            # Short silence, requires high confidence to stop.
            return embedding[1] > 0.9
        elif silence_duration <= self.max_silence_threshold_ms:  
            # Medium silence, requires medium confidence to stop.
            return embedding[1] > 0.8
        else:
            # Force stop if the user has been silent for a while.
            return True
       
         
    def get_silence_duration(self, conn):
        """
        Gets the current silence duration from the base VAD model.

        Args:
            conn: The connection object.

        Returns:
            int: The duration of silence in milliseconds.
        """
        return self.base_vad_model.get_silence_duration(conn)
    def _get_embedding(self, text: str):
        """
        Retrieves the text embedding from the Volcengine model.

        Args:
            text (str): The input text to get the embedding for.

        Returns:
            list: The embedding vector.
            bool: True if the embedding is from cache, False otherwise.

        Raises:
            Exception: If the API call to the embedding model fails.
        """
        if not text or not text.strip():
            return [1.0, 0.0]
        if self.cached_text == text:
            return self.cached_embedding, True
        try:
            logger.bind(tag=TAG).debug(f"调用嵌入模型:  model: {self.model_name},  input:{text}")
            response = self.client.embeddings.create(
                model=self.model_name,
                 encoding_format="float",
                input=text
            )
            embedding = response.data[0].embedding
            self.cached_text = text
            self.cached_embedding = embedding
            return embedding, False
        except Exception as e:
            logger.bind(tag=TAG).error(f"调用嵌入模型失败: {str(e)}")
            raise
