"""
Audio Recorder Utility for ASR Testing

Simple command-line based audio recorder that supports cross-platform recording.
"""

import os
import sys
import wave
import time
import platform
from typing import Optional

try:
    import pyaudio
except ImportError:
    print("❌ Error: pyaudio not installed")
    print("   Install with: pip install pyaudio")
    sys.exit(1)


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        format: int = pyaudio.paInt16
    ):
        """
        Initialize audio recorder
        
        Args:
            sample_rate: Sampling rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            chunk_size: Audio buffer size
            format: Audio format (default: 16-bit PCM)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = format
        self.audio = pyaudio.PyAudio()
        
    def record_audio(self, output_path: Optional[str] = None) -> str:
        """
        Record audio with interactive command-line control
        
        Args:
            output_path: Path to save the WAV file (optional)
            
        Returns:
            Path to the saved audio file
        """
        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                os.path.dirname(__file__),
                "tmp",
                f"recording_{timestamp}.wav"
            )
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print("\n🎤 Audio Recorder")
        print(f"   Sample Rate: {self.sample_rate} Hz")
        print(f"   Channels: {self.channels} (Mono)")
        print(f"   Format: 16-bit PCM")
        print(f"\n📁 Output: {output_path}\n")
        
        # Wait for user to start recording
        input("▶️  Press Enter to start recording...")
        
        print("\n🔴 Recording... Press Enter to stop")
        
        # Open audio stream
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        recording = True
        start_time = time.time()
        
        # Start recording in a separate thread to allow keyboard interrupt
        import threading
        
        def record_frames():
            while recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    print(f"⚠️  Warning: {e}")
                    break
        
        record_thread = threading.Thread(target=record_frames, daemon=True)
        record_thread.start()
        
        # Wait for user to stop recording
        try:
            input()
        except KeyboardInterrupt:
            print("\n")
        
        recording = False
        record_thread.join(timeout=1.0)
        
        duration = time.time() - start_time
        
        # Stop and close stream
        stream.stop_stream()
        stream.close()
        
        print(f"⏹️  Recording stopped ({duration:.1f}s)")
        
        # Save to WAV file
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ Audio saved: {file_size:.1f} KB\n")
        
        return output_path
    
    def cleanup(self):
        """Clean up PyAudio resources"""
        self.audio.terminate()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def record_audio_file(output_path: Optional[str] = None) -> str:
    """
    Convenient function to record audio file
    
    Args:
        output_path: Path to save the WAV file (optional)
        
    Returns:
        Path to the saved audio file
    """
    with AudioRecorder() as recorder:
        return recorder.record_audio(output_path)


if __name__ == "__main__":
    """
    Test the audio recorder
    
    Usage:
        python3 -m core.providers.asr.test.audio_recorder
        python3 -m core.providers.asr.test.audio_recorder output.wav
    """
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        audio_path = record_audio_file(output_file)
        print(f"🎉 Recording completed: {audio_path}")
        
        # Play audio on macOS
        if platform.system() == "Darwin":
            print("\n🔊 Playing back audio...")
            os.system(f"afplay '{audio_path}'")
            
    except KeyboardInterrupt:
        print("\n\n👋 Recording cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

