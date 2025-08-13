import time
import sys
import os
import platform
import numpy as np
import opuslib_next
from pathlib import Path
from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase

TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    def __init__(self, config):
        logger.bind(tag=TAG).info("TenVAD ONNX", config)
        
        # Configuration
        self.sample_rate = config.get("sample_rate", 16000)
        self.hop_size = config.get("hop_size", 256)  # TEN VAD's frame size (16ms at 16kHz)
        self.frame_size = config.get("frame_size", 512)  # Our processing frame size
        
        # VAD thresholds
        threshold = config.get("threshold", "0.5")
        threshold_low = config.get("threshold_low", "0.2")
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")

        self.vad_threshold = float(threshold) if threshold else 0.5
        self.vad_threshold_low = float(threshold_low) if threshold_low else 0.2
        self.silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )

        # Frame window threshold for voice detection
        self.frame_window_threshold = config.get("frame_window_threshold", 3)
        
        # Model path
        self.model_path = config.get("model_path", "models/ten-vad-onnx")
        
        # Initialize TEN VAD ONNX model
        self.ten_vad_working = False
        self.vad_model = None
        
        try:
            self._initialize_ten_vad_onnx()
            logger.bind(tag=TAG).info(
                f"TEN VAD ONNX initialized successfully - hop_size: {self.hop_size}, "
                f"threshold: {self.vad_threshold}"
            )
            self.ten_vad_working = True
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize TEN VAD ONNX: {e}")
            logger.bind(tag=TAG).warning(
                "TEN VAD ONNX initialization failed. Falling back to simple energy-based detection."
            )
            self.ten_vad_working = False

        # Initialize Opus decoder
        self.decoder = opuslib_next.Decoder(self.sample_rate, 1)
        
        logger.bind(tag=TAG).info(
            f"TEN VAD ONNX provider initialized - working: {self.ten_vad_working}, "
            f"threshold: {self.vad_threshold}, threshold_low: {self.vad_threshold_low}, "
            f"silence_threshold: {self.silence_threshold_ms}ms"
        )

    def _initialize_ten_vad_onnx(self):
        """Initialize TEN VAD ONNX model"""
        # Add the model path to Python path
        model_path = Path(self.model_path).resolve()
        if not model_path.exists():
            raise FileNotFoundError(f"TEN VAD ONNX model path not found: {model_path}")
        
        # Log platform information
        current_platform = platform.system()
        current_arch = platform.machine()
        logger.bind(tag=TAG).info(f"Initializing TEN VAD ONNX on {current_platform} {current_arch}")
        
        # Verify platform-specific libraries exist
        self._verify_platform_libraries(model_path, current_platform, current_arch)
        
        # Add model directory to Python path
        sys.path.insert(0, str(model_path))
        
        try:
            # Import the TEN VAD ONNX implementation
            from ten_vad import TenVad
            
            # Create TEN VAD instance
            self.vad_model = TenVad(
                hop_size=self.hop_size,
                threshold=self.vad_threshold
            )
            
            logger.bind(tag=TAG).info(f"TEN VAD ONNX model loaded successfully from {model_path}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load TEN VAD ONNX: {e}")
            raise
        finally:
            # Remove from Python path to avoid conflicts
            if str(model_path) in sys.path:
                sys.path.remove(str(model_path))

    def _verify_platform_libraries(self, model_path, current_platform, current_arch):
        """Verify that the required platform-specific libraries exist"""
        library_paths = []
        
        if current_platform == "Linux" and current_arch in ["x86_64", "x64"]:
            library_paths = [
                model_path / "lib" / "Linux" / "x64" / "libten_vad.so",
                model_path / "ten_vad_library" / "libten_vad.so"
            ]
        elif current_platform == "Darwin":  # macOS
            library_paths = [
                model_path / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad",
                model_path / "ten_vad_library" / "libten_vad"
            ]
        elif current_platform == "Windows":
            if current_arch.upper() in ['X64', 'X86_64', 'AMD64']:
                library_paths = [
                    model_path / "lib" / "Windows" / "x64" / "ten_vad.dll",
                    model_path / "ten_vad_library" / "ten_vad.dll"
                ]
            else:
                library_paths = [
                    model_path / "lib" / "Windows" / "x86" / "ten_vad.dll",
                    model_path / "ten_vad_library" / "ten_vad.dll"
                ]
        else:
            raise NotImplementedError(f"Unsupported platform: {current_platform} {current_arch}")
        
        # Check if at least one library path exists
        library_found = False
        for lib_path in library_paths:
            if lib_path.exists():
                library_found = True
                logger.bind(tag=TAG).debug(f"Found TEN VAD library: {lib_path}")
                break
        
        if not library_found:
            missing_paths = [str(p) for p in library_paths]
            raise FileNotFoundError(
                f"TEN VAD ONNX library not found for {current_platform} {current_arch}. "
                f"Expected one of: {missing_paths}"
            )

    def is_vad(self, conn, opus_packet):
        """
        Detect voice activity using TEN VAD ONNX
        
        Args:
            conn: Connection object with audio buffer and voice state
            opus_packet: Opus encoded audio packet
            
        Returns:
            bool: True if voice activity detected, False otherwise
        """
        try:
            # Decode Opus packet to PCM
            pcm_frame = self.decoder.decode(opus_packet, 960)
            conn.client_audio_buffer.extend(pcm_frame)

            # Process complete frames from buffer
            client_have_voice = False
            while len(conn.client_audio_buffer) >= self.frame_size * 2:
                # Extract frame (frame_size samples = frame_size * 2 bytes)
                chunk = conn.client_audio_buffer[:self.frame_size * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[self.frame_size * 2:]

                # Convert to numpy array
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0

                # Run TEN VAD ONNX detection or fallback
                if self.ten_vad_working and self.vad_model:
                    try:
                        # TEN VAD ONNX expects int16 audio data with specific hop_size
                        if len(audio_int16) >= self.hop_size:
                            # Take the first hop_size samples for TEN VAD
                            vad_chunk = audio_int16[:self.hop_size].astype(np.int16)
                            
                            # TEN VAD process method returns (probability, flags)
                            speech_prob, flags = self.vad_model.process(vad_chunk)
                            
                            # Use the probability for detection
                            if isinstance(speech_prob, (list, tuple)):
                                speech_prob = speech_prob[0] if len(speech_prob) > 0 else 0.0
                            elif hasattr(speech_prob, 'item'):
                                speech_prob = speech_prob.item()
                            else:
                                speech_prob = float(speech_prob)
                        else:
                            # Not enough data for TEN VAD processing
                            speech_prob = 0.0
                            
                    except Exception as e:
                        logger.bind(tag=TAG).warning(f"TEN VAD ONNX processing error: {e}")
                        # Fall back to simple energy-based detection
                        speech_prob = self._simple_energy_detection(audio_float32)
                else:
                    # Use simple energy-based detection as fallback
                    speech_prob = self._simple_energy_detection(audio_float32)

                # Apply dual threshold logic
                if speech_prob >= self.vad_threshold:
                    is_voice = True
                elif speech_prob <= self.vad_threshold_low:
                    is_voice = False
                else:
                    # Maintain previous state if in between thresholds
                    is_voice = getattr(conn, 'last_is_voice', False)

                # Update connection state
                conn.last_is_voice = is_voice

                # Update sliding window for voice detection
                if not hasattr(conn, 'client_voice_window'):
                    conn.client_voice_window = []
                
                conn.client_voice_window.append(is_voice)
                
                # Keep window size manageable
                if len(conn.client_voice_window) > 10:
                    conn.client_voice_window.pop(0)

                # Determine if voice is present based on window
                voice_count = conn.client_voice_window.count(True)
                client_have_voice = (voice_count >= self.frame_window_threshold)

                # Handle voice stop detection
                if getattr(conn, 'client_have_voice', False) and not client_have_voice:
                    current_time = time.time() * 1000
                    last_activity = getattr(conn, 'last_activity_time', current_time)
                    stop_duration = current_time - last_activity
                    
                    if stop_duration >= self.silence_threshold_ms:
                        conn.client_voice_stop = True
                        logger.bind(tag=TAG).debug(
                            f"Voice stop detected after {stop_duration:.0f}ms silence"
                        )

                # Update activity time if voice detected
                if client_have_voice:
                    conn.client_have_voice = True
                    conn.last_activity_time = time.time() * 1000

                # Log detection results periodically
                if hasattr(conn, '_vad_log_counter'):
                    conn._vad_log_counter += 1
                else:
                    conn._vad_log_counter = 1
                    
                if conn._vad_log_counter % 50 == 0:  # Log every 50 frames
                    vad_type = "TEN-ONNX" if self.ten_vad_working else "Energy"
                    logger.bind(tag=TAG).debug(
                        f"TEN VAD ONNX ({vad_type}): prob={speech_prob:.3f}, voice={client_have_voice}, "
                        f"window={voice_count}/{len(conn.client_voice_window)}"
                    )

            return client_have_voice

        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).warning(f"Opus decode error: {e}")
            return False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in TEN VAD ONNX processing: {e}")
            return False

    def _simple_energy_detection(self, audio_float32):
        """
        Simple energy-based voice detection as fallback
        
        Args:
            audio_float32: Audio data as float32 numpy array
            
        Returns:
            float: Voice probability (0.0 to 1.0)
        """
        try:
            # Calculate RMS energy
            rms_energy = np.sqrt(np.mean(audio_float32 ** 2))
            
            # Simple threshold-based detection
            # Adjust these values based on your environment
            energy_threshold_high = 0.01  # High energy threshold
            energy_threshold_low = 0.005  # Low energy threshold
            
            if rms_energy > energy_threshold_high:
                return 0.8  # High probability of voice
            elif rms_energy > energy_threshold_low:
                return 0.4  # Medium probability
            else:
                return 0.1  # Low probability
                
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Error in simple energy detection: {e}")
            return 0.0

    def __del__(self):
        """Cleanup resources when VAD provider is destroyed"""
        try:
            if hasattr(self, 'vad_model') and self.vad_model and self.ten_vad_working:
                # TEN VAD ONNX cleanup is handled automatically by the library
                pass
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Error during TEN VAD ONNX cleanup: {e}")