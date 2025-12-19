"""
FSMN VAD Stream Test Script (ONNX Version)

This script tests FSMN VAD ONNX with audio files, simulating the streaming behavior:

1. Load an audio file
2. Convert to 16kHz mono PCM
3. Split into 60ms chunks (simulating WebSocket protocol)
4. Feed chunks to FSMN VAD ONNX stream
5. Print VAD events (START_OF_SPEECH, END_OF_SPEECH)

Usage:
    python test_fsmn_vad_stream.py <audio_file>
    python test_fsmn_vad_stream.py --help

Example:
    python test_fsmn_vad_stream.py test_audio.wav
    python test_fsmn_vad_stream.py test_audio.mp3
"""

import asyncio
import argparse
import time
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Audio Loading Utilities
# ============================================================================

def load_audio_file(file_path: str, target_sample_rate: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Load audio file and convert to target sample rate.
    
    Args:
        file_path: Path to audio file (wav, mp3, etc.)
        target_sample_rate: Target sample rate (default 16000Hz)
    
    Returns:
        Tuple of (audio_samples as int16 numpy array, sample_rate)
    """
    try:
        import librosa
    except ImportError:
        print("Error: librosa is required. Install with: pip install librosa")
        sys.exit(1)
    
    print(f"Loading audio file: {file_path}")
    
    # Load audio with librosa (auto-converts to mono, resamples)
    audio, sr = librosa.load(file_path, sr=target_sample_rate, mono=True)
    
    # Convert float32 [-1, 1] to int16 [-32768, 32767]
    audio_int16 = (audio * 32767).astype(np.int16)
    
    duration = len(audio_int16) / target_sample_rate
    print(f"  Sample rate: {sr}Hz")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Samples: {len(audio_int16)}")
    
    return audio_int16, sr


def split_audio_to_chunks(audio: np.ndarray, chunk_duration_ms: int, sample_rate: int) -> List[bytes]:
    """
    Split audio into fixed-duration chunks.
    
    Args:
        audio: Audio samples as int16 numpy array
        chunk_duration_ms: Duration of each chunk in milliseconds
        sample_rate: Sample rate in Hz
    
    Returns:
        List of PCM byte chunks
    """
    samples_per_chunk = int(chunk_duration_ms * sample_rate / 1000)
    chunks = []
    
    for i in range(0, len(audio), samples_per_chunk):
        chunk = audio[i:i + samples_per_chunk]
        # Pad last chunk if necessary
        if len(chunk) < samples_per_chunk:
            chunk = np.pad(chunk, (0, samples_per_chunk - len(chunk)), mode='constant')
        chunks.append(chunk.tobytes())
    
    print(f"Split into {len(chunks)} chunks of {chunk_duration_ms}ms each")
    return chunks


# ============================================================================
# VAD Event Types (copied to avoid import issues)
# ============================================================================

class VADEventType(Enum):
    """VAD event types"""
    START_OF_SPEECH = "start_of_speech"
    INFERENCE_DONE = "inference_done"
    END_OF_SPEECH = "end_of_speech"


@dataclass
class VADEvent:
    """VAD event data structure"""
    type: VADEventType
    speech_duration: float = 0.0
    silence_duration: float = 0.0
    speaking: bool = False
    audio_data: bytes = b""
    inference_duration: float = 0.0
    
    def __repr__(self) -> str:
        audio_len_ms = len(self.audio_data) / 32 if self.audio_data else 0
        return (
            f"VADEvent(type={self.type.value}, "
            f"speaking={self.speaking}, "
            f"speech={self.speech_duration:.2f}s, "
            f"silence={self.silence_duration:.2f}s, "
            f"audio={audio_len_ms:.0f}ms, "
            f"inference={self.inference_duration*1000:.1f}ms)"
        )


# ============================================================================
# FSMN VAD Test Runner
# ============================================================================

class FsmnVADTester:
    """Test FSMN VAD ONNX with audio file input"""
    
    def __init__(
        self,
        model_dir: str = "models/fsmn_vad_onnx",
        quantize: bool = True,
        chunk_size_ms: int = 100,
        min_silence_duration_ms: int = 500,
        speech_noise_threshold: float = 0.6,
        sil_to_speech_time_thres: int = 150,
        prefix_padding_duration: float = 0.3,
    ):
        self.model_dir = model_dir
        self.quantize = quantize
        self.chunk_size_ms = chunk_size_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_noise_threshold = speech_noise_threshold
        self.sil_to_speech_time_thres = sil_to_speech_time_thres
        self.prefix_padding_duration = prefix_padding_duration
        self.sample_rate = 16000
        
        # Initialize FSMN ONNX model
        self._init_model()
    
    def _init_model(self):
        """Initialize FSMN VAD ONNX model"""
        try:
            from funasr_onnx import Fsmn_vad_online
        except ImportError:
            print("Error: funasr_onnx is required. Install with: pip install funasr-onnx")
            sys.exit(1)
        
        print(f"\nInitializing FSMN VAD ONNX model from {self.model_dir}...")
        self.model = Fsmn_vad_online(
            model_dir=self.model_dir,
            quantize=self.quantize,
            max_end_sil=self.min_silence_duration_ms,
        )
        
        # Override VAD parameters at runtime
        vad_opts = self.model.vad_scorer.vad_opts
        vad_opts.max_end_silence_time = self.min_silence_duration_ms
        vad_opts.speech_noise_thres = self.speech_noise_threshold
        vad_opts.sil_to_speech_time_thres = self.sil_to_speech_time_thres
        
        print(f"Model initialized (quantize={self.quantize}).")
        print(f"  max_end_silence_time: {vad_opts.max_end_silence_time}ms")
        print(f"  speech_noise_thres: {vad_opts.speech_noise_thres}")
        print(f"  sil_to_speech_time_thres: {vad_opts.sil_to_speech_time_thres}ms")
    
    def process_audio_file(self, file_path: str, input_chunk_ms: int = 60, verbose: bool = False) -> List[dict]:
        """
        Process audio file through FSMN VAD.
        
        Args:
            file_path: Path to audio file
            input_chunk_ms: Input chunk size in milliseconds (simulating WebSocket)
        
        Returns:
            List of VAD events with timestamps
        """
        # Load and split audio
        audio, sr = load_audio_file(file_path, self.sample_rate)
        input_chunks = split_audio_to_chunks(audio, input_chunk_ms, self.sample_rate)
        
        # FSMN processing parameters
        chunk_samples = int(self.chunk_size_ms * self.sample_rate / 1000)
        chunk_bytes = chunk_samples * 2  # int16
        
        # Buffers
        input_buffer = bytearray()
        inference_buffer = bytearray()
        
        # Prefix padding
        prefix_padding_bytes = int(self.prefix_padding_duration * self.sample_rate) * 2
        max_speech_bytes = 60 * self.sample_rate * 2 + prefix_padding_bytes
        speech_buffer = bytearray(max_speech_bytes)
        speech_buffer_index = 0
        
        # State
        fsmn_param_dict = {"in_cache": [], "is_final": False}
        speaking = False
        speech_start_ms = 0
        speech_duration = 0.0
        silence_duration = 0.0
        
        # Results
        events = []
        current_time_ms = 0
        total_inference_time = 0.0
        inference_count = 0
        
        print(f"\n{'='*60}")
        print(f"Processing audio with FSMN VAD")
        print(f"{'='*60}")
        print(f"Input chunk size: {input_chunk_ms}ms")
        print(f"FSMN chunk size: {self.chunk_size_ms}ms")
        print(f"Min silence duration: {self.min_silence_duration_ms}ms")
        print(f"Prefix padding: {self.prefix_padding_duration*1000:.0f}ms")
        print()
        
        def reset_write_cursor():
            nonlocal speech_buffer_index
            if speech_buffer_index <= prefix_padding_bytes:
                return
            padding_data = speech_buffer[
                speech_buffer_index - prefix_padding_bytes : speech_buffer_index
            ]
            speech_buffer[: prefix_padding_bytes] = padding_data
            speech_buffer_index = prefix_padding_bytes
        
        # Process chunks
        for chunk_idx, pcm_chunk in enumerate(input_chunks):
            input_buffer.extend(pcm_chunk)
            inference_buffer.extend(pcm_chunk)
            current_time_ms += input_chunk_ms
            
            # Process complete FSMN chunks
            while len(inference_buffer) >= chunk_bytes:
                inference_start = time.perf_counter()
                
                # Convert to float32
                chunk_int16 = np.frombuffer(inference_buffer[:chunk_bytes], dtype=np.int16)
                chunk_float32 = chunk_int16.astype(np.float32) / 32768.0
                
                # Run FSMN ONNX inference
                res = self.model(chunk_float32, param_dict=fsmn_param_dict)
                
                inference_duration = time.perf_counter() - inference_start
                total_inference_time += inference_duration
                inference_count += 1
                
                # Verbose output: show raw FSMN result
                if verbose:
                    print(f"   [{current_time_ms:6.0f}ms] inference #{inference_count:3d} | "
                          f"result={res} | "
                          f"time={inference_duration*1000:.2f}ms")
                
                # Copy to speech buffer
                available_space = len(speech_buffer) - speech_buffer_index
                to_copy = min(available_space, chunk_bytes)
                if to_copy > 0:
                    speech_buffer[speech_buffer_index:speech_buffer_index + to_copy] = input_buffer[:to_copy]
                    speech_buffer_index += to_copy
                
                # Parse FSMN ONNX result: [[[start, end], ...]]
                if res and len(res) > 0 and len(res[0]) > 0:
                    seg = res[0][0]  # First segment from first batch
                    seg_start, seg_end = seg[0], seg[1]
                    
                    if seg_start >= 0 and seg_end == -1:
                        # Speech start
                        if not speaking:
                            speaking = True
                            speech_start_ms = seg_start
                            silence_duration = 0.0
                            
                            audio_data = bytes(speech_buffer[:speech_buffer_index])
                            events.append({
                                "time_ms": current_time_ms,
                                "type": "START_OF_SPEECH",
                                "seg_start_ms": seg_start,
                                "audio_duration_ms": len(audio_data) / 32,
                                "inference_ms": inference_duration * 1000,
                            })
                            print(f"🎤 [{current_time_ms:6.0f}ms] START_OF_SPEECH @{seg_start}ms | "
                                  f"audio={len(audio_data)/32:.0f}ms | "
                                  f"inference={inference_duration*1000:.1f}ms")
                    
                    elif seg_start == -1 and seg_end > 0:
                        # Speech end
                        if speaking:
                            speaking = False
                            speech_duration_ms = seg_end - speech_start_ms
                            speech_duration = speech_duration_ms / 1000
                            
                            audio_data = bytes(speech_buffer[:speech_buffer_index])
                            events.append({
                                "time_ms": current_time_ms,
                                "type": "END_OF_SPEECH",
                                "seg_end_ms": seg_end,
                                "speech_duration_ms": speech_duration_ms,
                                "audio_duration_ms": len(audio_data) / 32,
                                "inference_ms": inference_duration * 1000,
                            })
                            print(f"🔇 [{current_time_ms:6.0f}ms] END_OF_SPEECH @{seg_end}ms | "
                                  f"speech={speech_duration:.2f}s | "
                                  f"audio={len(audio_data)/32:.0f}ms | "
                                  f"inference={inference_duration*1000:.1f}ms")
                            
                            # Reset state
                            speech_duration = 0.0
                            fsmn_param_dict = {"in_cache": [], "is_final": False}
                            reset_write_cursor()
                    
                    elif seg_start > 0 and seg_end > 0:
                        # Short segment (ignored)
                        print(f"   [{current_time_ms:6.0f}ms] SHORT_SEGMENT [{seg_start}, {seg_end}]ms (ignored)")
                
                # Update state
                if speaking:
                    speech_duration += self.chunk_size_ms / 1000
                else:
                    silence_duration += self.chunk_size_ms / 1000
                    reset_write_cursor()
                
                # Remove processed data
                del inference_buffer[:chunk_bytes]
                del input_buffer[:to_copy]
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Summary")
        print(f"{'='*60}")
        print(f"Total input chunks: {len(input_chunks)}")
        print(f"Total FSMN inferences: {inference_count}")
        print(f"Total inference time: {total_inference_time*1000:.1f}ms")
        print(f"Average inference time: {total_inference_time/inference_count*1000:.1f}ms" if inference_count > 0 else "N/A")
        print(f"Speech segments detected: {len([e for e in events if e['type'] == 'START_OF_SPEECH'])}")
        
        return events


def main():
    parser = argparse.ArgumentParser(
        description="Test FSMN VAD ONNX with audio file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_fsmn_vad_stream.py test_audio.wav
    python test_fsmn_vad_stream.py test_audio.mp3 --input-chunk-ms 100
    python test_fsmn_vad_stream.py test_audio.wav --min-silence-ms 800
    python test_fsmn_vad_stream.py test_audio.wav --no-quantize
        """
    )
    
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to audio file (wav, mp3, etc.)"
    )
    
    parser.add_argument(
        "--model-dir",
        type=str,
        default="models/fsmn_vad_onnx",
        help="ONNX model directory (default: models/fsmn_vad_onnx)"
    )
    
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Use FP32 model instead of INT8 quantized model"
    )
    
    parser.add_argument(
        "--input-chunk-ms",
        type=int,
        default=60,
        help="Input chunk size in milliseconds (default: 60, simulating WebSocket protocol)"
    )
    
    parser.add_argument(
        "--fsmn-chunk-ms",
        type=int,
        default=100,
        help="FSMN inference chunk size in milliseconds (default: 100)"
    )
    
    parser.add_argument(
        "--min-silence-ms",
        type=int,
        default=500,
        help="Minimum silence duration to detect speech end (default: 500)"
    )
    
    parser.add_argument(
        "--speech-noise-threshold",
        type=float,
        default=0.6,
        help="Speech noise threshold (default: 0.6)"
    )
    
    parser.add_argument(
        "--sil-to-speech-time",
        type=int,
        default=150,
        help="Silence to speech transition time in ms (default: 150)"
    )
    
    parser.add_argument(
        "--prefix-padding",
        type=float,
        default=0.3,
        help="Prefix padding duration in seconds (default: 0.3)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show raw FSMN inference output for each chunk"
    )
    
    args = parser.parse_args()
    
    # Validate audio file
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    # Create tester and run
    tester = FsmnVADTester(
        model_dir=args.model_dir,
        quantize=not args.no_quantize,
        chunk_size_ms=args.fsmn_chunk_ms,
        min_silence_duration_ms=args.min_silence_ms,
        speech_noise_threshold=args.speech_noise_threshold,
        sil_to_speech_time_thres=args.sil_to_speech_time,
        prefix_padding_duration=args.prefix_padding,
    )
    
    events = tester.process_audio_file(
        args.audio_file,
        input_chunk_ms=args.input_chunk_ms,
        verbose=args.verbose,
    )
    
    print(f"\n{'='*60}")
    print(f"All Events")
    print(f"{'='*60}")
    for event in events:
        print(f"  {event}")


if __name__ == "__main__":
    main()

