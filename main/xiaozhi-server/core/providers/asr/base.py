import os
import wave
import uuid
import queue
import asyncio
import traceback
import threading
import opuslib_next
import json
import io
import time
import concurrent.futures
import csv
from datetime import datetime
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List, Dict, Any
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import handleAudioMessage
from core.utils.asr_filter import ASRFilter

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self, config=None):
        self.config = config
        self.asr_filter = ASRFilter(config) if config else None

    # Open audio channels
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

    # Receive audio
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
            
        # Debug logging
        if not hasattr(conn, '_asr_log_counter'):
            conn._asr_log_counter = 0
        conn._asr_log_counter += 1
        
        if conn._asr_log_counter % 200 == 0 or (have_voice and conn._asr_log_counter % 50 == 0):
            logger.bind(tag=TAG).debug(f"ASR receive_audio: have_voice={have_voice}, "
                                     f"client_have_voice={conn.client_have_voice}, "
                                     f"audio_len={len(audio)}, asr_buffer_len={len(conn.asr_audio)}")

        # Echo suppression: Ignore audio for a brief period after starting to listen
        if hasattr(conn, 'listen_start_time'):
            time_since_listen_start = time.time() - conn.listen_start_time
            if time_since_listen_start < 0.1:  # Ignore first 300ms of audio (echo period)
                if have_voice:
                    logger.bind(tag=TAG).debug(f"Ignoring potential echo audio ({time_since_listen_start:.2f}s after listen start)")
                have_voice = False

        # Always add audio to pre-buffer (rolling buffer)
        conn.audio_pre_buffer.append(audio)
        
        # If voice is detected and we're not already collecting
        if have_voice and not conn.client_have_voice:
            # Clear the just_started_listening flag when actual voice is detected
            if hasattr(conn, 'just_started_listening'):
                conn.just_started_listening = False
            # Add pre-buffered audio to the beginning of ASR audio
            conn.asr_audio = list(conn.audio_pre_buffer) + conn.asr_audio
            conn.audio_pre_buffer.clear()
        
        conn.asr_audio.append(audio)
        if not have_voice and not conn.client_have_voice:
            conn.asr_audio = conn.asr_audio[-10:]
            return

        if conn.client_voice_stop:
            # Check if we just started listening - if so, skip this audio
            if hasattr(conn, 'just_started_listening') and conn.just_started_listening:
                logger.bind(tag=TAG).debug("Skipping stale audio chunks after listen start")
                conn.just_started_listening = False
                conn.asr_audio.clear()
                conn.reset_vad_states()
                return
                
            asr_audio_task = conn.asr_audio.copy()
            conn.asr_audio.clear()
            conn.reset_vad_states()

            if len(asr_audio_task) > 20:  # Increased from 15 to 20 chunks (1.2 seconds)
                logger.bind(tag=TAG).debug(f"Processing {len(asr_audio_task)} audio chunks")
                await self.handle_voice_stop(conn, asr_audio_task)

    # Handle voice stop
    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """Parallel processing of ASR and voiceprint recognition"""
        try:
            total_start_time = time.monotonic()

            # Prepare audio data
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)

            combined_pcm_data = b"".join(pcm_data)

            # Pre-prepare WAV data
            wav_data = None
            # Use connection's voiceprint provider
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)

            # Define ASR task

            def run_asr():
                start_time = time.monotonic()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self.speech_to_text(
                                asr_audio_task, conn.session_id, conn.audio_format)
                        )
                        end_time = time.monotonic()
                        logger.bind(tag=TAG).info(
                            f"ASR time: {end_time - start_time:.3f}s")
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    end_time = time.monotonic()
                    logger.bind(tag=TAG).error(f"ASR failed: {e}")
                    return ("", None)

            # Define voiceprint recognition task
            def run_voiceprint():
                if not wav_data:
                    return None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Use connection's voiceprint provider
                        result = loop.run_until_complete(
                            conn.voiceprint_provider.identify_speaker(
                                wav_data, conn.session_id)
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Voiceprint recognition failed: {e}")
                    return None

            # Run in parallel using thread pool executor
            parallel_start_time = time.monotonic()

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as thread_executor:
                asr_future = thread_executor.submit(run_asr)

                if conn.voiceprint_provider and wav_data:
                    voiceprint_future = thread_executor.submit(run_voiceprint)

                    # Wait for both threads to complete
                    asr_result = asr_future.result(timeout=15)
                    voiceprint_result = voiceprint_future.result(timeout=15)

                    results = {"asr": asr_result,
                               "voiceprint": voiceprint_result}
                else:
                    asr_result = asr_future.result(timeout=15)
                    results = {"asr": asr_result, "voiceprint": None}

            # Process results
            raw_text, file_path = results.get("asr", ("", None))
            speaker_name = results.get("voiceprint", None)

            # Apply ASR filtering if enabled
            if self.asr_filter and raw_text:
                # Prepare context for filtering
                filter_context = {
                    'time_since_bot_utterance': time.time() - getattr(conn, 'last_bot_utterance_time', 0),
                    'expecting_response': getattr(conn, 'expecting_user_response', False),
                    'recent_filtered': getattr(conn, 'recent_filtered_texts', [])[-5:]
                }
                
                should_filter, reason = self.asr_filter.should_filter(raw_text, filter_context)
                
                if should_filter:
                    logger.bind(tag=TAG).info(f"Filtered transcript: '{raw_text}' - Reason: {reason}")
                    # Track filtered texts
                    if not hasattr(conn, 'recent_filtered_texts'):
                        conn.recent_filtered_texts = []
                    conn.recent_filtered_texts.append(raw_text)
                    # Keep only last 10 filtered texts
                    conn.recent_filtered_texts = conn.recent_filtered_texts[-10:]
                    self.stop_ws_connection()
                    return

            # Log recognition results
            if raw_text:
                logger.bind(tag=TAG).info(f"Recognized text: {raw_text}")
            if speaker_name:
                logger.bind(tag=TAG).info(
                    f"Identified speaker: {speaker_name}")

            # Performance monitoring
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).info(
                f"Total processing time: {total_time:.3f}s")

            # Check text length
            text_len, _ = remove_punctuation_and_length(raw_text)
            self.stop_ws_connection()

            if text_len > 0:
                # Build JSON string with speaker information
                enhanced_text = self._build_enhanced_text(
                    raw_text, speaker_name)

                # Use custom module for reporting
                await startToChat(conn, enhanced_text)
                enqueue_asr_report(conn, enhanced_text, asr_audio_task)

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to handle voice stop: {e}")
            import traceback
            logger.bind(tag=TAG).debug(
                f"Exception details: {traceback.format_exc()}")

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """Build text with speaker information"""
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
            logger.bind(tag=TAG).warning(
                "PCM data is empty, cannot convert to WAV")
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

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """Save PCM data as WAV file"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    def log_audio_transcript(self, file_path: str, audio_length_seconds: float, transcript: str):
        """Log audio file information to CSV file"""
        try:
            # Create logs directory at the same level as output_dir
            log_dir = os.path.join(os.path.dirname(self.output_dir), "asr_logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # Create both CSV and JSON log files for easy inspection
            csv_log_file = os.path.join(log_dir, f"asr_log_{datetime.now().strftime('%Y%m%d')}.csv")
            json_log_file = os.path.join(log_dir, f"asr_log_{datetime.now().strftime('%Y%m%d')}.json")
            
            # Write to CSV file
            csv_exists = os.path.exists(csv_log_file)
            with open(csv_log_file, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'filename', 'file_path', 'audio_length_seconds', 'transcript']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not csv_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'timestamp': datetime.now().isoformat(),
                    'filename': os.path.basename(file_path),
                    'file_path': file_path,
                    'audio_length_seconds': round(audio_length_seconds, 2),
                    'transcript': transcript
                })
            
            # Also write to JSON file for easier parsing
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'audio_length_seconds': round(audio_length_seconds, 2),
                'transcript': transcript
            }
            
            # Read existing JSON logs or create new list
            json_logs = []
            if os.path.exists(json_log_file):
                try:
                    with open(json_log_file, 'r', encoding='utf-8') as f:
                        json_logs = json.load(f)
                except:
                    json_logs = []
            
            json_logs.append(log_entry)
            
            # Write updated JSON logs
            with open(json_log_file, 'w', encoding='utf-8') as f:
                json.dump(json_logs, f, ensure_ascii=False, indent=2)
            
            # Also create a simple text log for quick inspection
            txt_log_file = os.path.join(log_dir, f"asr_log_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(txt_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Filename: {os.path.basename(file_path)}\n")
                f.write(f"Full Path: {file_path}\n")
                f.write(f"Audio Length: {audio_length_seconds:.2f} seconds\n")
                f.write(f"Transcript: {transcript}\n")
                f.write(f"{'='*80}\n")
                
            # Logging disabled - comment out the log message
            # logger.bind(tag=TAG).info(
            #     f"Logged ASR transcript to {log_dir} - File: {os.path.basename(file_path)}, "
            #     f"Length: {audio_length_seconds:.2f}s, Transcript: {transcript[:50]}..."
            # )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to log audio transcript: {e}")

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """Decode Opus audio data to PCM data"""
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
                    logger.bind(tag=TAG).warning(
                        f"Opus decode error, skipping packet {i}: {e}")
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Audio processing error, packet {i}: {e}")

            return pcm_data

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error occurred during audio decoding: {e}")
            return []
