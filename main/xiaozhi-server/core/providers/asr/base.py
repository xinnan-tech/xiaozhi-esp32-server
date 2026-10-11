import os
import io
import wave
import uuid
import json
import time
import queue
import shutil
import asyncio
import tempfile
import traceback
import threading

from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import handleAudioMessage
from typing import Optional, Tuple, List, NamedTuple, TYPE_CHECKING


if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # Open the audio-processing channels.
    async def open_audio_channels(self, conn: "ConnectionHandler"):
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # Process ASR audio in order.
    def asr_text_priority_thread(self, conn: "ConnectionHandler"):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to process ASR text: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"
                )
                continue

    # Receive audio input.
    async def receive_audio(self, conn: "ConnectionHandler", audio, audio_have_voice):
        if conn.client_listen_mode == "manual":
            # Manual mode: buffer audio for ASR recognition.
            conn.asr_audio.append(audio)
        else:
            # Automatic or real-time mode: use VAD detection.
            conn.asr_audio.append(audio)

            # Keep only a small tail when no speech has been detected yet.
            if not audio_have_voice and not conn.client_have_voice:
                conn.asr_audio = conn.asr_audio[-10:]
                return

            # Trigger recognition when VAD marks the end of speech.
            if conn.asr.interface_type != InterfaceType.STREAM and conn.client_voice_stop:
                # 直接使用asr_audio中的PCM数据
                pcm_bytes = b"".join(conn.asr_audio)
                # 检查是否有足够的音频数据（每帧1920字节，15帧约28800字节）
                if len(pcm_bytes) > 1920 * 15:
                    await self.handle_voice_stop(conn, [pcm_bytes])
                conn.reset_audio_states()

                if len(asr_audio_task) > 15:
                    await self.handle_voice_stop(conn, asr_audio_task)

    # Handle the end of speech.
    async def handle_voice_stop(self, conn: "ConnectionHandler", asr_audio_task: List[bytes]):
        """Run ASR and speaker recognition in parallel."""
        try:
            total_start_time = time.monotonic()

            # Prepare the audio data.
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)

            combined_pcm_data = b"".join(pcm_data)

            # Build WAV data in advance if voiceprint is enabled.
            wav_data = None
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)

            # Start the ASR task.
            asr_task = self.speech_to_text_wrapper(
                asr_audio_task, conn.session_id
            )

            if conn.voiceprint_provider and wav_data:
                voiceprint_task = conn.voiceprint_provider.identify_speaker(
                    wav_data, conn.session_id
                )
                # Wait for both tasks concurrently.
                asr_result, voiceprint_result = await asyncio.gather(
                    asr_task, voiceprint_task, return_exceptions=True
                )
            else:
                asr_result = await asr_task
                voiceprint_result = None

            # Record recognition results and handle exceptions.
            if isinstance(asr_result, Exception):
                logger.bind(tag=TAG).error(f"ASR recognition failed: {asr_result}")
                raw_text = ""
            else:
                raw_text, _ = asr_result

            if isinstance(voiceprint_result, Exception):
                logger.bind(tag=TAG).error(
                    f"Voiceprint identification failed: {voiceprint_result}"
                )
                speaker_name = ""
            else:
                speaker_name = voiceprint_result

            # Normalize the ASR result shape.
            if isinstance(raw_text, dict):
                # FunASR can return a structured dict.
                if speaker_name:
                    raw_text["speaker"] = speaker_name

                # Log the recognition result.
                if raw_text.get("language"):
                    logger.bind(tag=TAG).info(
                        f"Detected language: {raw_text['language']}"
                    )
                if raw_text.get("emotion"):
                    logger.bind(tag=TAG).info(
                        f"Detected emotion: {raw_text['emotion']}"
                    )
                if raw_text.get("content"):
                    logger.bind(tag=TAG).info(
                        f"Recognized text: {raw_text['content']}"
                    )
                if speaker_name:
                    logger.bind(tag=TAG).info(f"Detected speaker: {speaker_name}")

                # Convert to a JSON string for downstream processing.
                enhanced_text = json.dumps(raw_text, ensure_ascii=False)
                content_for_length_check = raw_text.get("content", "")
            else:
                # Other ASR providers can return plain text.
                if raw_text:
                    logger.bind(tag=TAG).info(f"Recognized text: {raw_text}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"Detected speaker: {speaker_name}")

                # Wrap speaker metadata when needed.
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                content_for_length_check = raw_text

            # Performance monitoring.
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).debug(f"Total processing time: {total_time:.3f}s")

            # Check the text length before continuing.
            text_len, _ = remove_punctuation_and_length(content_for_length_check)
            self.stop_ws_connection()

            if text_len > 0:
                audio_snapshot = asr_audio_task.copy()
                enqueue_asr_report(conn, enhanced_text, audio_snapshot)
                # Use the custom reporting flow.
                await startToChat(conn, enhanced_text)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to handle end-of-speech: {e}")
            import traceback

            logger.bind(tag=TAG).debug(
                f"Exception details: {traceback.format_exc()}"
            )

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """Build text with speaker metadata for plain-text ASR results."""
        if speaker_name and speaker_name.strip():
            return json.dumps(
                {"speaker": speaker_name, "content": text}, ensure_ascii=False
            )
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM data into WAV format."""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM data is empty; cannot convert to WAV")
            return b""

        # Ensure the PCM payload has an even byte length for 16-bit audio.
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]

        # Build the WAV file header.
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16 kHz sample rate
                wav_file.writeframes(pcm_data)

            wav_buffer.seek(0)
            wav_data = wav_buffer.read()

            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV conversion failed: {e}")
            return b""

    def stop_ws_connection(self):
        pass

    async def close(self):
        pass

    class AudioArtifacts(NamedTuple):
        pcm_frames: List[bytes]
        """List of PCM audio frames."""
        pcm_bytes: bytes
        """Combined PCM audio bytes."""
        file_path: Optional[str]
        """WAV file path."""
        temp_path: Optional[str]
        """Temporary WAV file path."""

    def get_current_artifacts(self) -> Optional["ASRProviderBase.AudioArtifacts"]:
        return self._current_artifacts

    def requires_file(self) -> bool:
        """Whether this provider requires file input."""
        return False

    def prefers_temp_file(self) -> bool:
        """Whether this provider prefers a temporary file."""
        return False

    def build_temp_file(self, pcm_bytes: bytes) -> Optional[str]:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_bytes)
            return temp_path
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to create temporary audio file: {e}")
            return None

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """Save PCM data as a WAV file."""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    async def speech_to_text_wrapper(
        self, pcm_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        temp_path = None
        try:
            combined_pcm_data = b"".join(pcm_data)

            free_space = shutil.disk_usage(self.output_dir).free
            if free_space < len(combined_pcm_data) * 2:
                raise OSError("Insufficient disk space")

            if self.requires_file() and self.prefers_temp_file():
                temp_path = self.build_temp_file(combined_pcm_data)

            if (hasattr(self, "delete_audio_file") and not self.delete_audio_file) or (
                self.requires_file() and not self.prefers_temp_file()
            ):
                file_path = self.save_audio_to_file(pcm_data, session_id)

            if len(combined_pcm_data) == 0:
                artifacts = None
            else:
                artifacts = ASRProviderBase.AudioArtifacts(
                    pcm_frames=pcm_data,
                    pcm_bytes=combined_pcm_data,
                    file_path=file_path,
                    temp_path=temp_path,
                )

            text, _ = await self.speech_to_text(
                pcm_data, session_id, artifacts
            )
            return text, file_path
        except OSError as e:
            logger.bind(tag=TAG).error(f"File operation error: {e}")
            return None, None
        except Exception as e:
            logger.bind(tag=TAG).error(f"Speech recognition failed: {e}")
            return None, None
        finally:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                if (
                    hasattr(self, "delete_audio_file")
                    and self.delete_audio_file
                    and file_path
                    and os.path.exists(file_path)
                ):
                    os.remove(file_path)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to clean up audio files: {e}")

    @abstractmethod
    async def speech_to_text(
        self,
        opus_data: List[bytes],
        session_id: str,
        artifacts: Optional[AudioArtifacts] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data into text.

        :param opus_data: Input Opus audio data.
        :param session_id: Session ID.
        :param audio_format: Audio format, default `"opus"`.
        :param artifacts: Audio artifacts including PCM data and file paths.
        :return: Recognized text and file path, if available.
        """
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """Decode Opus audio packets into PCM data."""
        decoder = None
        try:
            decoder = opuslib_next.Decoder(16000, 1)
            pcm_data = []
            buffer_size = 960  # Process 960 samples per frame (60 ms at 16 kHz).

            for i, opus_packet in enumerate(opus_data):
                try:
                    if not opus_packet or len(opus_packet) == 0:
                        continue

                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame and len(pcm_frame) > 0:
                        pcm_data.append(pcm_frame)

                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(
                        f"Opus decode error; skipping packet {i}: {e}"
                    )
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Audio processing error for packet {i}: {e}"
                    )

            return pcm_data

        except Exception as e:
            logger.bind(tag=TAG).error(f"Audio decoding failed: {e}")
            return []
        finally:
            if decoder is not None:
                try:
                    del decoder
                except Exception as e:
                    logger.bind(tag=TAG).debug(
                        f"Failed to release decoder resources: {e}"
                    )
