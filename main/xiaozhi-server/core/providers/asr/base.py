import os
import io
import wave
import uuid
import json
import time
import queue
import asyncio
import traceback
import threading
import opuslib_next
from datetime import datetime
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length, check_for_noise
from core.handle.receiveAudioHandle import handleAudioMessage

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # Open audio channel
    async def open_audio_channels(self, conn):
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # Process ASR audio in order
    def asr_text_priority_thread(self, conn):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                
                # STRICT GATE: Drop audio if client is supposed to be speaking (prevent self-echo/voxing)
                if conn.client_is_speaking:
                    # Clear the queue to discard accumulated echo
                    while not conn.asr_audio_queue.empty():
                        try:
                            conn.asr_audio_queue.get_nowait()
                        except queue.Empty:
                            break
                    logger.bind(tag=TAG).debug("Dropped ASR packet/cleared queue because client_is_speaking=True")
                    continue

                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to process ASR text: {str(e)}, Type: {type(e).__name__}, Stack: {traceback.format_exc()}"
                )
                continue

    # Receive audio
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "manual":
            # Manual mode: Cache audio for ASR recognition
            conn.asr_audio.append(audio)
        else:
            # Auto/Real-time mode: Use VAD detection
            have_voice = audio_have_voice

            conn.asr_audio.append(audio)
            if not have_voice and not conn.client_have_voice:
                conn.asr_audio = conn.asr_audio[-10:]
                return

            # Trigger recognition when voice stop detected by VAD in auto mode
            if conn.client_voice_stop:
                asr_audio_task = conn.asr_audio.copy()
                conn.asr_audio.clear()
                conn.reset_vad_states()

                if len(asr_audio_task) > 15:
                    await self.handle_voice_stop(conn, asr_audio_task)

    # Handle voice stop
    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """Process ASR and voiceprint recognition in parallel"""
        try:
            total_start_time = time.monotonic()

            # Prepare audio data
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)

            combined_pcm_data = b"".join(pcm_data)

            # Energy-based Noise Filtering:
            # Drop audio if it matches the criteria (Short & Low Energy)
            if check_for_noise(combined_pcm_data):
                logger.bind(tag=TAG).debug(f"Dropped audio packet due to low energy/noise (Size: {len(combined_pcm_data)})")
                return

            # Prepare WAV data in advance
            wav_data = None
            if (conn.voiceprint_provider or conn.config.get("gemini_speech_to_model")) and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)

            # Speech-to-Model check
            if conn.config.get("llm", {}).get("provider") == "gemini" and conn.config.get("gemini_speech_to_model"):
                logger.bind(tag=TAG).info("Speech-to-Model enabled for Gemini, bypassing ASR.")
                speaker_name = ""
                if conn.voiceprint_provider and wav_data:
                    try:
                        speaker_name = await conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Voiceprint failed in Speech-to-Model: {e}")
                
                enhanced_text = self._build_enhanced_text("[Speech Input]", speaker_name)
                await startToChat(conn, enhanced_text, audio_data=wav_data)
                return

            # Define ASR task
            asr_task = self.speech_to_text(asr_audio_task, conn.session_id, conn.audio_format, client_id=getattr(conn, "client_id", None))

            if conn.voiceprint_provider and wav_data:
                voiceprint_task = conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                # Wait for both results concurrently
                asr_result, voiceprint_result = await asyncio.gather(
                    asr_task, voiceprint_task, return_exceptions=True
                )
            else:
                asr_result = await asr_task
                voiceprint_result = None

            # Record recognition results - check for exceptions
            if isinstance(asr_result, Exception):
                logger.bind(tag=TAG).error(f"ASR recognition failed: {asr_result}")
                raw_text = ""
            else:
                raw_text, _ = asr_result

            if isinstance(voiceprint_result, Exception):
                logger.bind(tag=TAG).error(f"Voiceprint recognition failed: {voiceprint_result}")
                speaker_name = ""
            else:
                speaker_name = voiceprint_result

            # Determine ASR result type
            if isinstance(raw_text, dict):
                # Dict format returned by FunASR
                if speaker_name:
                    raw_text["speaker"] = speaker_name

                # Record recognition results
                if raw_text.get("language"):
                    logger.bind(tag=TAG).info(f"Detected language: {raw_text['language']}")
                if raw_text.get("emotion"):
                    logger.bind(tag=TAG).info(f"Detected emotion: {raw_text['emotion']}")
                if raw_text.get("content"):
                    logger.bind(tag=TAG).info(f"Detected text: {raw_text['content']}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"Identified speaker: {speaker_name}")

                # Convert to JSON string for downstream
                enhanced_text = json.dumps(raw_text, ensure_ascii=False)
                content_for_length_check = raw_text.get("content", "")
            else:
                # Plain text returned by other ASRs
                if raw_text:
                    logger.bind(tag=TAG).info(f"Detected text: {raw_text}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"Identified speaker: {speaker_name}")

                # Build JSON string containing speaker info
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                content_for_length_check = raw_text

            # Performance monitoring
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).debug(f"Total processing time: {total_time:.3f}s")

            # Check text length
            text_len, _ = remove_punctuation_and_length(content_for_length_check)
            self.stop_ws_connection()

            if text_len > 0:
                # Use custom module for reporting
                await startToChat(conn, enhanced_text)
                enqueue_asr_report(conn, enhanced_text, asr_audio_task)
            elif content_for_length_check:
                logger.bind(tag=TAG).info(f"Ignored noise/hallucination: {content_for_length_check}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to handle voice stop: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"Exception details: {traceback.format_exc()}")

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """Build text containing speaker info (only for plain text ASR)"""
        if speaker_name and speaker_name.strip():
            return json.dumps({
                "speaker": speaker_name,
                "content": text
            }, ensure_ascii=False)
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM data to WAV format"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM data is empty, cannot convert to WAV")
            return b""
        
        # Ensure data length is even (16-bit audio)
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        
        # Create WAV file header
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)      # Mono
                wav_file.setsampwidth(2)      # 16-bit
                wav_file.setframerate(16000)  # 16kHz sample rate
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV conversion failed: {e}")
            return b""

    def stop_ws_connection(self):
        pass

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str, client_id: str = None) -> str:
        """Save PCM data as WAV file"""
        if client_id:
            # Client-specific directory: data/{client_id}/
            # Get project root (assuming output_dir is relative to project root or use absolute path)
            # We'll assume current working directory is project root or close enough
            client_dir = os.path.join("data", client_id)
            if not os.path.exists(client_dir):
                os.makedirs(client_dir, exist_ok=True)
            
            # Timestamp suffix: YYMMDD-hhmmss-ffffff
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            file_name = f"ASR_{timestamp}.wav"
            file_path = os.path.join(client_dir, file_name)
        else:
            # Fallback to default behavior
            module_name = __name__.split(".")[-1]
            file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
            # output_dir from config
            file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    def save_audio_background(self, pcm_data: List[bytes], session_id: str, client_id: str = None) -> str:
        """Save PCM data as WAV file in background (non-blocking)"""
        # Generate path first
        if client_id:
            client_dir = os.path.join("data", client_id)
            if not os.path.exists(client_dir):
                os.makedirs(client_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            file_name = f"ASR_{timestamp}.wav"
            file_path = os.path.join(client_dir, file_name)
        else:
            module_name = __name__.split(".")[-1]
            file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
            file_path = os.path.join(self.output_dir, file_name)
            
        # Define write operation
        def _write():
            try:
                # Ensure directory exists (again, just in case of race/thread safety)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with wave.open(file_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"".join(pcm_data))
            except Exception as e:
                logger.bind(tag=TAG).error(f"Background audio save failed: {e}")

        # Fire and forget
        threading.Thread(target=_write, daemon=True).start()
        
        return file_path

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus", client_id: str = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """Decode Opus audio data to PCM data"""
        decoder = None
        try:
            decoder = opuslib_next.Decoder(16000, 1)
            pcm_data = []
            buffer_size = 960  # Process 960 samples each time (60ms at 16kHz)
            
            for i, opus_packet in enumerate(opus_data):
                try:
                    if not opus_packet or len(opus_packet) == 0:
                        continue
                    
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame and len(pcm_frame) > 0:
                        pcm_data.append(pcm_frame)
                        
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus decoding error, skipping packet {i}: {e}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Audio processing error, packet {i}: {e}")
            
            return pcm_data
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error during audio decoding process: {e}")
            return []
        finally:
            if decoder is not None:
                try:
                    del decoder
                except Exception as e:
                    logger.bind(tag=TAG).debug(f"Error releasing decoder resources: {e}")
