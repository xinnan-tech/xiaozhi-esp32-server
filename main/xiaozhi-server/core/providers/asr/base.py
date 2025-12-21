import os
import io
import wave
import uuid
import json
import time
import asyncio
import traceback
import threading
import opuslib_next
import concurrent.futures
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from .dto import ASRMessageType, ASRInputMessage, InterfaceType
from queue import Queue, Empty

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):

    def __init__(self):
        self.asr_input_queue = Queue[ASRInputMessage]()
        self.asr_input_audio_format = "pcm"
        # Default to non-streaming, subclasses can override
        self.interface_type = InterfaceType.NON_STREAM

    # 打开音频通道
    async def open_audio_channels(self, conn):
        # Thread for processing raw audio from WebSocket
        conn.asr_priority_thread = threading.Thread(
            target=self._asr_audio_queue_thread, 
            args=(conn,), 
            daemon=True
        )
        conn.asr_priority_thread.start()

        # Start VAD stream and event processor (must be in async context)
        await self._start_vad_stream(conn)
        
        # Thread for processing ASR input messages from VAD stream
        conn.asr_input_thread = threading.Thread(
            target=self._asr_input_queue_thread,
            args=(conn,),
            daemon=True
        )
        conn.asr_input_thread.start()
        logger.bind(tag=TAG).info("ASR input queue thread started")

    async def _start_vad_stream(self, conn):
        """Start VAD stream task and event processor
        
        This must be called from async context (running event loop).
        """
        from core.handle.abortHandle import handleAbortMessage
        
        if conn.vad_stream is None:
            logger.bind(tag=TAG).warning("VAD stream not initialized, skipping start")
            return
        
        try:
            # Start the VAD processing task
            await conn.vad_stream.start()
            
            # Start the event processor task
            conn._vad_event_task = asyncio.create_task(
                conn.vad_stream.process_events(
                    conn=conn,
                    asr_input_queue=self.asr_input_queue,
                    interrupt_callback=handleAbortMessage,
                )
            )
            logger.bind(tag=TAG).info("VAD stream and event processor started")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start VAD stream: {e}")

    def _asr_audio_queue_thread(self, conn):
        """Thread for processing raw audio from WebSocket"""
        # Import inside thread to avoid circular imports
        from core.handle.receiveAudioHandle import handleAudioMessage
        
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理ASR音频失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    def _asr_input_queue_thread(self, conn):
        """Thread for processing ASRInputMessage from VAD stream
        
        This thread receives audio chunks from VAD stream's process_events()
        and processes them when a LAST message is received (contains complete audio).
        """
        while not conn.stop_event.is_set():
            try:
                # Get message from async queue in sync context
                message: ASRInputMessage = self.asr_input_queue.get(timeout=0.5)
                
                # Process ASRInputMessage
                if message.message_type == ASRMessageType.FIRST:
                    # Start of new speech segment - just log, LAST contains complete audio
                    logger.bind(tag=TAG).debug(
                        f"ASR: Speech started, audio={message.audio_duration_ms:.0f}ms"
                    )
                    
                elif message.message_type == ASRMessageType.MIDDLE:
                    # For streaming ASR: would process incremental audio here
                    # Currently skipped by VAD event processor
                    pass
                    
                elif message.message_type == ASRMessageType.LAST:
                    # End of speech segment - LAST contains complete audio from VAD
                    # No need to accumulate with FIRST (would cause duplication)
                    total_audio_ms = message.audio_duration_ms
                    logger.bind(tag=TAG).info(
                        f"ASR: Speech ended, total_audio={total_audio_ms:.0f}ms, "
                        f"speech_duration={message.speech_duration:.2f}s"
                    )
                    
                    # Process the complete speech segment (LAST audio only)
                    asyncio.run_coroutine_threadsafe(
                        self._process_speech_segment(conn, [message.audio_data]),
                        conn.loop,
                    )
                    
            except asyncio.TimeoutError:
                continue
            except Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"ASR input queue error: {str(e)}, type: {type(e).__name__}"
                )
                continue
        
        logger.bind(tag=TAG).info("ASR input queue thread stopped")

    async def _process_speech_segment(
        self, 
        conn, 
        pcm_audio_chunks: list[bytes]
    ):
        """Process a complete speech segment (PCM audio from VAD)
        
        Args:
            conn: Connection handler
            pcm_audio_chunks: List of PCM audio chunks (already decoded)
        """
        # Import here to avoid circular imports
        from core.handle.receiveAudioHandle import startToChat
        
        try:
            total_start_time = time.monotonic()
            
            # Combine PCM chunks
            combined_pcm = b"".join(pcm_audio_chunks)
            
            # Prepare WAV data for voiceprint if needed
            wav_data = None
            if conn.voiceprint_provider and combined_pcm:
                wav_data = self._pcm_to_wav(combined_pcm)
            
            # Run ASR (audio is already PCM, not opus)
            def run_asr():
                start_time = time.monotonic()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Pass PCM data directly
                        result = loop.run_until_complete(
                            self.speech_to_text(pcm_audio_chunks, conn.session_id, self.asr_input_audio_format)
                        )
                        end_time = time.monotonic()
                        asr_elapsed_ms = (end_time - start_time) * 1000
                        
                        # Calculate E2E latency
                        e2e_asr_delay = 0
                        if hasattr(conn, '_latency_voice_end_time'):
                            e2e_asr_delay = time.time() * 1000 - conn._latency_voice_end_time
                        
                        logger.bind(tag=TAG).info(
                            f"🎙️ [Latency] ASR completed: {asr_elapsed_ms:.0f}ms | "
                            f"Voice end → ASR: {e2e_asr_delay:.0f}ms"
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"ASR failed: {e}")
                    return ("", None)
            
            # Run voiceprint recognition
            def run_voiceprint():
                if not wav_data:
                    return None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Voiceprint failed: {e}")
                    return None
            
            # Run tasks in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                asr_future = executor.submit(run_asr)
                
                if conn.voiceprint_provider and wav_data:
                    voiceprint_future = executor.submit(run_voiceprint)
                    asr_result = asr_future.result(timeout=15)
                    voiceprint_result = voiceprint_future.result(timeout=15)
                    results = {"asr": asr_result, "voiceprint": voiceprint_result}
                else:
                    asr_result = asr_future.result(timeout=15)
                    results = {"asr": asr_result, "voiceprint": None}
            
            # Process results
            raw_text, _ = results.get("asr", ("", None))
            speaker_name = results.get("voiceprint", None)
            
            if raw_text:
                logger.bind(tag=TAG).info(f"Recognized text: {raw_text}")
            if speaker_name:
                logger.bind(tag=TAG).info(f"Recognized speaker: {speaker_name}")
            
            # Performance monitoring
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).info(f"Total processing time: {total_time:.3f}s")
            
            # Check text length
            text_len, _ = remove_punctuation_and_length(raw_text)
            self.stop_ws_connection()
            
            if text_len > 0:
                # Append to ASR text buffer
                if conn.asr_text_buffer:
                    conn.asr_text_buffer += " " + raw_text
                else:
                    conn.asr_text_buffer = raw_text
                
                # Turn Detection: let turn detection handle end of turn
                if conn.turn_detection:
                    # Turn detection will wait for endpoint delay, then call on_end_of_turn
                    conn.turn_detection.check_end_of_turn(conn)
                    return
                
                # # No Turn Detection: process immediately
                # await conn.on_end_of_turn()
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                
                asr_report_time = int(time.time())
                
                await startToChat(conn, enhanced_text)
                # Note: For report, we need to convert PCM back to opus or use PCM directly
                # For now, pass empty list as audio data for report
                enqueue_asr_report(conn, enhanced_text, [], report_time=asr_report_time)
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Process speech segment failed: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"Exception details: {traceback.format_exc()}")

    # 接收音频
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
        
        conn.asr_audio.append(audio)
        if not have_voice and not conn.client_have_voice:
            conn.asr_audio = conn.asr_audio[-10:]
            return

        if conn.client_voice_stop:
            asr_audio_task = conn.asr_audio.copy()
            conn.asr_audio.clear()
            conn.reset_vad_states()

            if len(asr_audio_task) > 15 or conn.client_listen_mode == "manual":
                await self.handle_voice_stop(conn, asr_audio_task)

    # 处理语音停止
    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """并行处理ASR和声纹识别"""
        # Import here to avoid circular imports
        from core.handle.receiveAudioHandle import startToChat
        
        try:
            total_start_time = time.monotonic()
            
            # 准备音频数据
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)
            
            combined_pcm_data = b"".join(pcm_data)
            
            # 预先准备WAV数据
            wav_data = None
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)
            
            # 定义ASR任务
            def run_asr():
                start_time = time.monotonic()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self.speech_to_text(asr_audio_task, conn.session_id, conn.audio_format)
                        )
                        end_time = time.monotonic()
                        asr_elapsed_ms = (end_time - start_time) * 1000
                        
                        # 计算从用户说完到 ASR 完成的延迟
                        e2e_asr_delay = 0
                        if hasattr(conn, '_latency_voice_end_time'):
                            e2e_asr_delay = time.time() * 1000 - conn._latency_voice_end_time
                        
                        logger.bind(tag=TAG).info(
                            f"🎙️ [延迟追踪] ASR完成: {asr_elapsed_ms:.0f}ms | "
                            f"用户说完→ASR完成: {e2e_asr_delay:.0f}ms"
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    end_time = time.monotonic()
                    logger.bind(tag=TAG).error(f"ASR失败: {e}")
                    return ("", None)
            
            # 定义声纹识别任务
            def run_voiceprint():
                if not wav_data:
                    return None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # 使用连接的声纹识别提供者
                        result = loop.run_until_complete(
                            conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"声纹识别失败: {e}")
                    return None
            
            # 使用线程池执行器并行运行
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as thread_executor:
                asr_future = thread_executor.submit(run_asr)
                
                if conn.voiceprint_provider and wav_data:
                    voiceprint_future = thread_executor.submit(run_voiceprint)
                    
                    # 等待两个线程都完成
                    asr_result = asr_future.result(timeout=15)
                    voiceprint_result = voiceprint_future.result(timeout=15)
                    
                    results = {"asr": asr_result, "voiceprint": voiceprint_result}
                else:
                    asr_result = asr_future.result(timeout=15)
                    results = {"asr": asr_result, "voiceprint": None}
            
            
            # 处理结果
            raw_text, _ = results.get("asr", ("", None))
            speaker_name = results.get("voiceprint", None)
            
            # 记录识别结果
            if raw_text:
                logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
            if speaker_name:
                logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")
            
            # 性能监控
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).info(f"总处理耗时: {total_time:.3f}s")
            
            # 检查文本长度
            text_len, _ = remove_punctuation_and_length(raw_text)
            self.stop_ws_connection()
            
            if text_len > 0:
                # 构建包含说话人信息的JSON字符串
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                
                # Record the timestamp when ASR completed (for correct message ordering)
                asr_report_time = int(time.time())
                
                # 使用自定义模块进行上报
                await startToChat(conn, enhanced_text)
                enqueue_asr_report(conn, enhanced_text, asr_audio_task, report_time=asr_report_time)
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理语音停止失败: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"异常详情: {traceback.format_exc()}")

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """构建包含说话人信息的文本"""
        if speaker_name and speaker_name.strip():
            return json.dumps({
                "speaker": speaker_name,
                "content": text
            }, ensure_ascii=False)
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """将PCM数据转换为WAV格式"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM数据为空，无法转换WAV")
            return b""
        
        # 确保数据长度是偶数（16位音频）
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        
        # 创建WAV文件头
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)      # 单声道
                wav_file.setsampwidth(2)      # 16位
                wav_file.setframerate(16000)  # 16kHz采样率
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV转换失败: {e}")
            return b""

    def stop_ws_connection(self):
        pass

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """将Opus音频数据解码为PCM数据"""
        try:
            decoder = opuslib_next.Decoder(16000, 1)
            pcm_data = []
            buffer_size = 960  # 每次处理960个采样点 (60ms at 16kHz)
            
            for i, opus_packet in enumerate(opus_data):
                try:
                    if not opus_packet or len(opus_packet) == 0:
                        continue
                    
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame and len(pcm_frame) > 0:
                        pcm_data.append(pcm_frame)
                        
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus解码错误，跳过数据包 {i}: {e}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"音频处理错误，数据包 {i}: {e}")
            
            return pcm_data
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频解码过程发生错误: {e}")
            return []
