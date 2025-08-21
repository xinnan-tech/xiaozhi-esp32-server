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
                confidence_val = float(new_confidence)
                logger.debug(f"VAD confidence: {confidence_val:.3f}, RMS: {audio_rms:.4f}")
            
            # Reset model periodically to prevent memory growth
            curr_time = time.time()
            diff_time = curr_time - self._last_reset_time
            if diff_time >= _MODEL_RESET_STATES_TIME:
                self._model.reset_states()
                self._last_reset_time = curr_time
                
            return float(new_confidence)
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
        
    def is_vad(self, conn, opus_packet) -> bool:
        """Detect voice activity in Opus audio packet.
        
        This method maintains compatibility with the existing interface while
        using the new production-ready VAD analyzer internally.
        
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
                logger.bind(tag=TAG).info(f"VAD state: {vad_state.name}")
                self._last_logged_state = vad_state
            
            # Update connection state based on VAD state
            current_have_voice = vad_state in [VADState.SPEAKING, VADState.STARTING]
            
            # Handle silence detection for sentence end
            if conn.client_have_voice and not current_have_voice:
                if vad_state == VADState.QUIET:
                    stop_duration = time.time() * 1000 - conn.last_activity_time
                    if stop_duration >= self.silence_threshold_ms:
                        conn.client_voice_stop = True
                        logger.bind(tag=TAG).info(f"Voice stopped after {stop_duration}ms silence")
                        
            if current_have_voice:
                conn.client_have_voice = True
                conn.last_activity_time = time.time() * 1000
                
            # Update last voice state for compatibility
            if hasattr(conn, 'last_is_voice'):
                conn.last_is_voice = current_have_voice
                
            return current_have_voice
            
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"Decode error: {e}")
            return False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
            return False