"""
Opus encoding utility class
Encode PCM audio data to Opus format
"""

import logging
import traceback
import numpy as np
from typing import List, Optional
from opuslib_next import Encoder
from opuslib_next import constants


class OpusEncoderUtils:
    """PCM to Opus encoder"""

    def __init__(self, sample_rate: int, channels: int, frame_size_ms: int):
        """
        Initialize Opus encoder

        Args:
            sample_rate: Sample rate (Hz)
            channels: Number of channels (1=mono, 2=stereo)
            frame_size_ms: Frame size (milliseconds)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size_ms = frame_size_ms

        # Calculate samples per frame = sample rate * frame size(ms) / 1000
        self.frame_size = (sample_rate * frame_size_ms) // 1000

        # Total frame size = samples per frame * channels
        self.total_frame_size = self.frame_size * channels

        # Bitrate and complexity settings
        self.bitrate = 24000  # bps
        self.complexity = 10  # Highest quality

        # Initialize buffer as empty
        self.buffer = np.array([], dtype=np.int16)

        try:
            # Create Opus encoder
            self.encoder = Encoder(
                sample_rate, channels, constants.APPLICATION_AUDIO  # Audio optimization mode
            )
            self.encoder.bitrate = self.bitrate
            self.encoder.complexity = self.complexity
            self.encoder.signal = constants.SIGNAL_VOICE  # Voice signal optimization

        except Exception as e:
            logging.error(f"Failed to initialize Opus encoder: {e}")
            raise RuntimeError("Initialization failed") from e

    def reset_state(self):
        """Reset encoder state"""
        self.encoder.reset_state()
        self.buffer = np.array([], dtype=np.int16)

    def encode_pcm_to_opus(self, pcm_data: bytes, end_of_stream: bool) -> List[bytes]:
        """
        Encode PCM data to Opus format

        Args:
            pcm_data: PCM byte data
            end_of_stream: Whether this is the end of stream

        Returns:
            List of Opus data packets
        """
        # Convert byte data to short array
        new_samples = self._convert_bytes_to_shorts(pcm_data)

        # Validate PCM data
        self._validate_pcm_data(new_samples)

        # Append new data to buffer
        self.buffer = np.append(self.buffer, new_samples)

        opus_packets = []
        offset = 0

        # Process all complete frames
        while offset <= len(self.buffer) - self.total_frame_size:
            frame = self.buffer[offset: offset + self.total_frame_size]
            output = self._encode(frame)
            if output:
                opus_packets.append(output)
            offset += self.total_frame_size

        # Keep unprocessed samples
        self.buffer = self.buffer[offset:]

        # Process remaining data at end of stream
        if end_of_stream and len(self.buffer) > 0:
            # Create last frame and pad with zeros
            last_frame = np.zeros(self.total_frame_size, dtype=np.int16)
            last_frame[: len(self.buffer)] = self.buffer
            output = self._encode(last_frame)
            if output:
                opus_packets.append(output)
            self.buffer = np.array([], dtype=np.int16)

        return opus_packets

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode one frame of audio data"""
        try:
            # Convert numpy array to bytes
            frame_bytes = frame.tobytes()
            # opuslib requires input byte count to be multiple of channels*2
            encoded = self.encoder.encode(frame_bytes, self.frame_size)
            return encoded
        except Exception as e:
            logging.error(f"Opus encoding failed: {e}")
            traceback.print_exc()
            return None

    def _convert_bytes_to_shorts(self, bytes_data: bytes) -> np.ndarray:
        """Convert byte array to short array (16-bit PCM)"""
        # Assume input is little-endian 16-bit PCM
        return np.frombuffer(bytes_data, dtype=np.int16)

    def _validate_pcm_data(self, pcm_shorts: np.ndarray) -> None:
        """Validate PCM data validity"""
        # 16-bit PCM data range is -32768 to 32767
        if np.any((pcm_shorts < -32768) | (pcm_shorts > 32767)):
            invalid_samples = pcm_shorts[(
                pcm_shorts < -32768) | (pcm_shorts > 32767)]
            logging.warning(
                f"Found invalid PCM samples: {invalid_samples[:5]}...")
            # In practice, you can choose to clip instead of throwing exception
            # np.clip(pcm_shorts, -32768, 32767, out=pcm_shorts)

    def close(self):
        """Close encoder and release resources"""
        # opuslib doesn't have explicit close method, Python's garbage collection will handle it
        pass
