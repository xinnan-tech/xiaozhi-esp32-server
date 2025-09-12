"""Silero Voice Activity Detection (VAD) implementation using ONNX.

This module provides a production-ready VAD implementation based on the Silero VAD ONNX model,
with support for 8kHz and 16kHz sample rates, state management, and advanced features.
"""

import time
from typing import Optional
import numpy as np
import opuslib_next
from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase
from core.providers.vad.vad_analyzer import VADAnalyzer, VADParams, VADState

TAG = __name__
logger = setup_logging()

# How often should we reset internal model state
_MODEL_RESET_STATES_TIME = 5.0

try:
    import onnxruntime
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error("In order to use Silero ONNX VAD, you need to `pip install onnxruntime`.")
    raise Exception(f"Missing module(s): {e}")


class SileroOnnxModel:
    """ONNX runtime wrapper for the Silero VAD model.
    
    Provides voice activity detection using the pre-trained Silero VAD model
    with ONNX runtime for efficient inference.
    """
    
    def __init__(self, path: str, force_onnx_cpu: bool = True):
        """Initialize the Silero ONNX model.
        
        Args:
            path: Path to the ONNX model file
            force_onnx_cpu: Whether to force CPU execution provider
        """
        opts = onnxruntime.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        
        if force_onnx_cpu and "CPUExecutionProvider" in onnxruntime.get_available_providers():
            self.session = onnxruntime.InferenceSession(
                path, providers=["CPUExecutionProvider"], sess_options=opts
            )
        else:
            self.session = onnxruntime.InferenceSession(path, sess_options=opts)
            
        self.reset_states()
        self.sample_rates = [8000, 16000]
        
    def _validate_input(self, x: np.ndarray, sr: int):
        """Validate and preprocess input audio data."""
        if np.ndim(x) == 1:
            x = np.expand_dims(x, 0)
        if np.ndim(x) > 2:
            raise ValueError(f"Too many dimensions for input audio chunk {x.ndim}")
            
        if sr not in self.sample_rates:
            raise ValueError(
                f"Supported sampling rates: {self.sample_rates} (sample rate: {sr})"
            )
        if sr / np.shape(x)[1] > 31.25:
            raise ValueError("Input audio chunk is too short")
            
        return x, sr
        
    def reset_states(self, batch_size: int = 1):
        """Reset the internal model states.
        
        Args:
            batch_size: Batch size for state initialization
        """
        self._state = np.zeros((2, batch_size, 128), dtype="float32")
        self._context = np.zeros((batch_size, 0), dtype="float32")
        self._last_sr = 0
        self._last_batch_size = 0
        
    def __call__(self, x: np.ndarray, sr: int) -> np.ndarray:
        """Process audio input through the VAD model."""
        x, sr = self._validate_input(x, sr)
        num_samples = 512 if sr == 16000 else 256
        
        if np.shape(x)[-1] != num_samples:
            raise ValueError(
                f"Provided number of samples is {np.shape(x)[-1]} "
                f"(Supported values: 256 for 8000 sample rate, 512 for 16000)"
            )
            
        batch_size = np.shape(x)[0]
        context_size = 64 if sr == 16000 else 32
        
        if not self._last_batch_size:
            self.reset_states(batch_size)
        if (self._last_sr) and (self._last_sr != sr):
            self.reset_states(batch_size)
        if (self._last_batch_size) and (self._last_batch_size != batch_size):
            self.reset_states(batch_size)
            
        if not np.shape(self._context)[1]:
            self._context = np.zeros((batch_size, context_size), dtype="float32")
            
        x = np.concatenate((self._context, x), axis=1)
        
        if sr in [8000, 16000]:
            ort_inputs = {"input": x, "state": self._state, "sr": np.array(sr, dtype="int64")}
            ort_outs = self.session.run(None, ort_inputs)
            out, state = ort_outs
            self._state = state
        else:
            raise ValueError()
            
        self._context = x[..., -context_size:]
        self._last_sr = sr
        self._last_batch_size = batch_size
        
        return out


class SileroVADAnalyzer(VADAnalyzer):
    """Voice Activity Detection analyzer using the Silero VAD ONNX model.
    
    Implements VAD analysis using the pre-trained Silero ONNX model for
    accurate voice activity detection. Supports 8kHz and 16kHz sample rates
    with automatic model state management.
    """
    
    def __init__(self, model_path: str, *, sample_rate: Optional[int] = None, 
                 params: Optional[VADParams] = None):
        """Initialize the Silero VAD analyzer.
        
        Args:
            model_path: Path to the ONNX model file
            sample_rate: Audio sample rate (8000 or 16000 Hz)
            params: VAD parameters for detection thresholds and timing
        """
        super().__init__(sample_rate=sample_rate, params=params)
        
        logger.debug("Loading Silero ONNX VAD model...")
        self._model = SileroOnnxModel(model_path, force_onnx_cpu=True)
        self._last_reset_time = 0
        logger.debug("Loaded Silero ONNX VAD")
        
        # Initialize sample rate if provided
        if sample_rate:
            self.set_sample_rate(sample_rate)
        
    def set_sample_rate(self, sample_rate: int):
        """Set the sample rate for audio processing.
        
        Args:
            sample_rate: Audio sample rate (must be 8000 or 16000 Hz)
            
        Raises:
            ValueError: If sample rate is not 8000 or 16000 Hz
        """
        if sample_rate != 16000 and sample_rate != 8000:
            raise ValueError(
                f"Silero VAD sample rate needs to be 16000 or 8000 (sample rate: {sample_rate})"
            )
        super().set_sample_rate(sample_rate)
        
    def num_frames_required(self) -> int:
        """Get the number of audio frames required for VAD analysis.
        
        Returns:
            Number of frames required (512 for 16kHz, 256 for 8kHz)
        """
        return 512 if self.sample_rate == 16000 else 256
        
    def reset(self):
        """Reset the VAD analyzer and model states."""
        super().reset()
        self._model.reset_states()
        self._last_reset_time = time.time()
        
    def voice_confidence(self, buffer: bytes) -> float:
        """Calculate voice activity confidence for the given audio buffer.
        
        Args:
            buffer: Audio buffer to analyze
            
        Returns:
            Voice confidence score between 0.0 and 1.0
        """
        try:
            audio_int16 = np.frombuffer(buffer, np.int16)
            # Divide by 32768 because we have signed 16-bit data
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            new_confidence = self._model(audio_float32, self.sample_rate)[0]
            
            # Log confidence values periodically for debugging
            if not hasattr(self, '_confidence_log_counter'):
                self._confidence_log_counter = 0
            self._confidence_log_counter += 1
            
            if self._confidence_log_counter % 100 == 0:  # Log every 100th frame (reduced from 10)
                audio_rms = float(np.sqrt(np.mean(audio_float32 ** 2)))
                confidence_val = float(new_confidence.item())  # Use .item() to extract scalar from numpy array
                logger.debug(f"VAD confidence: {confidence_val:.3f}, RMS: {audio_rms:.4f}")
            
            # Reset model periodically to prevent memory growth
            curr_time = time.time()
            diff_time = curr_time - self._last_reset_time
            if diff_time >= _MODEL_RESET_STATES_TIME:
                self._model.reset_states()
                self._last_reset_time = curr_time
                
            return float(new_confidence.item())  # Use .item() to extract scalar from numpy array
        except Exception as e:
            logger.error(f"Error analyzing audio with Silero ONNX VAD: {e}")
            return 0.0


class VADProvider(VADProviderBase):
    """Production-ready Silero ONNX VAD provider implementation.
    
    This provider uses the ONNX-based Silero VAD model with advanced state management,
    volume detection, and configurable parameters for production use.
    """
    
    def __init__(self, config):
        """Initialize the VAD provider.
        
        Args:
            config: Configuration dictionary with VAD parameters
        """
        logger.bind(tag=TAG).info("Initializing Silero ONNX VAD", config)
        
        # Load ONNX model
        model_path = config.get("model_path", "models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx")
        
        # Initialize decoder for Opus packets
        self.decoder = opuslib_next.Decoder(16000, 1)
        
        # Create VAD parameters from config
        params = VADParams(
            confidence=float(config.get("threshold", "0.5")),
            start_secs=float(config.get("start_secs", "0.2")),
            stop_secs=float(config.get("stop_secs", "0.8")),
            min_volume=float(config.get("min_volume", "0.001"))  # Very low default for better sensitivity
        )
        
        logger.bind(tag=TAG).info(f"VAD params: confidence={params.confidence}, "
                                f"start_secs={params.start_secs}, stop_secs={params.stop_secs}, "
                                f"min_volume={params.min_volume}")
        
        # Get silence duration for compatibility
        self.silence_threshold_ms = int(config.get("min_silence_duration_ms", "1000"))
        
        # Initialize VAD analyzer
        self.analyzer = SileroVADAnalyzer(
            model_path=model_path,
            sample_rate=16000,
            params=params
        )
        
        logger.bind(tag=TAG).info("Silero ONNX VAD initialized successfully")
        
    def reset(self):
        """Reset the VAD provider internal states."""
        self.analyzer.reset()
        
    async def is_vad(self, conn, opus_packet) -> bool:
        """Detect voice activity in Opus audio packet and stream to ASR.
        
        This method handles VAD detection and streaming to ASR in real-time,
        replacing the old buffer-based approach.
        
        Args:
            conn: Connection object with client state
            opus_packet: Opus encoded audio packet
            
        Returns:
            True if voice activity is detected, False otherwise
        """
        try:
            # Decode Opus packet to PCM
            pcm_frame = self.decoder.decode(opus_packet, 960)
            
            # Analyze audio and get VAD state
            vad_state = self.analyzer.analyze_audio(pcm_frame)
            
            # Log VAD state for debugging (only log state changes)
            if not hasattr(self, '_last_logged_state') or self._last_logged_state != vad_state:
                logger.bind(tag=TAG).info(f"[VAD-STATE] VAD state changed to: {vad_state.name} for {conn.session_id}")
                self._last_logged_state = vad_state
            
            # Update connection state based on VAD state
            # Include STOPPING state because it still contains speech that should be processed
            current_have_voice = vad_state in [VADState.SPEAKING, VADState.STARTING, VADState.STOPPING]
            
            # Handle streaming session management based on VAD state
            if vad_state == VADState.STARTING and not getattr(conn, 'asr_streaming_active', False):
                # Start streaming session when voice begins
                logger.bind(tag=TAG).info(f"[VAD-START] Voice activity detected - starting ASR streaming session for {conn.session_id}")
                if hasattr(conn, 'asr_provider'):
                    logger.bind(tag=TAG).debug(f"[VAD-START] ASR provider found: {type(conn.asr_provider).__name__}")
                    success = await conn.asr_provider.start_streaming_session(conn, conn.session_id)
                    if success:
                        conn.asr_streaming_active = True
                        conn.asr_stream_start_time = time.time()
                        logger.bind(tag=TAG).info(f"[VAD-START] ASR streaming session started successfully for {conn.session_id}")
                    else:
                        logger.bind(tag=TAG).error(f"[VAD-START] Failed to start ASR streaming session for {conn.session_id}")
                else:
                    logger.bind(tag=TAG).error(f"[VAD-START] No ASR provider found on connection {conn.session_id}")
            
            # Stream audio during voice activity
            streaming_active = getattr(conn, 'asr_streaming_active', False)
            logger.bind(tag=TAG).info(f"[VAD-STREAM] Audio streaming check - streaming_active={streaming_active}, current_have_voice={current_have_voice}, vad_state={vad_state.name}")
            
            if streaming_active and current_have_voice:
                if hasattr(conn, 'asr_provider'):
                    # Stream the PCM audio chunk to ASR
                    logger.bind(tag=TAG).info(f"[VAD-STREAM] Streaming {len(pcm_frame)} bytes to ASR for {conn.session_id}")
                    partial_result = await conn.asr_provider.stream_audio_chunk(conn, pcm_frame, conn.session_id)
                    if partial_result:
                        logger.bind(tag=TAG).info(f"[VAD-STREAM] Partial transcript from ASR: '{partial_result}'")
                        conn.latest_partial_transcript = partial_result
                else:
                    logger.bind(tag=TAG).error(f"[VAD-STREAM] ASR provider not found on connection {conn.session_id}")
            elif streaming_active:
                logger.bind(tag=TAG).debug(f"[VAD-STREAM] Streaming session active but no voice detected (state: {vad_state}) for {conn.session_id}")
            elif current_have_voice:
                logger.bind(tag=TAG).debug(f"[VAD-STREAM] Voice detected but no streaming session active for {conn.session_id}")
            
            # Handle end of voice activity
            if vad_state == VADState.QUIET and getattr(conn, 'asr_streaming_active', False):
                # Check if enough silence has passed to end the session
                if not hasattr(conn, 'silence_start_time'):
                    conn.silence_start_time = time.time()
                    logger.bind(tag=TAG).debug(f"[VAD-END] Starting silence timer for {conn.session_id}")
                
                silence_duration_ms = (time.time() - conn.silence_start_time) * 1000
                if silence_duration_ms >= self.silence_threshold_ms:
                    logger.bind(tag=TAG).info(f"[VAD-END] Voice ended after {silence_duration_ms:.0f}ms silence - ending ASR streaming session for {conn.session_id}")
                    
                    if hasattr(conn, 'asr_provider'):
                        # End the streaming session and get final transcript
                        logger.bind(tag=TAG).debug(f"[VAD-END] Calling end_streaming_session for {conn.session_id}")
                        final_transcript, file_path = await conn.asr_provider.end_streaming_session(conn, conn.session_id)
                        
                        if final_transcript.strip():
                            logger.bind(tag=TAG).info(f"[VAD-END] Final transcript received: '{final_transcript}'")
                            
                            # Process the final transcript (same as old system)
                            from core.handle.receiveAudioHandle import startToChat
                            logger.bind(tag=TAG).info(f"[VAD-END] Sending transcript to chat handler for {conn.session_id}")
                            await startToChat(conn, final_transcript)
                        else:
                            logger.bind(tag=TAG).warning(f"[VAD-END] No speech detected in streaming session for {conn.session_id}")
                    else:
                        logger.bind(tag=TAG).error(f"[VAD-END] No ASR provider found for {conn.session_id}")
                    
                    # Reset streaming state
                    conn.asr_streaming_active = False
                    if hasattr(conn, 'silence_start_time'):
                        delattr(conn, 'silence_start_time')
                    if hasattr(conn, 'asr_stream_start_time'):
                        delattr(conn, 'asr_stream_start_time')
                    if hasattr(conn, 'latest_partial_transcript'):
                        delattr(conn, 'latest_partial_transcript')
                    logger.bind(tag=TAG).info(f"[VAD-END] Streaming state reset for {conn.session_id}")
                else:
                    logger.bind(tag=TAG).debug(f"[VAD-END] Silence duration {silence_duration_ms:.0f}ms < threshold {self.silence_threshold_ms}ms for {conn.session_id}")
            else:
                # Reset silence timer if voice is detected again
                if hasattr(conn, 'silence_start_time'):
                    logger.bind(tag=TAG).debug(f"[VAD-END] Resetting silence timer for {conn.session_id}")
                    delattr(conn, 'silence_start_time')
            
            # Update legacy connection state for compatibility
            if current_have_voice:
                conn.client_have_voice = True
                conn.last_activity_time = time.time() * 1000
            else:
                conn.client_have_voice = False
                
            # Update last voice state for compatibility
            if hasattr(conn, 'last_is_voice'):
                conn.last_is_voice = current_have_voice
                
            return current_have_voice
            
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"Decode error: {e}")
            return False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"Traceback: {traceback.format_exc()}")
            return False