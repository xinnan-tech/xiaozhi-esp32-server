"""
Simple Audio Player for LiveKit Agent
Uses session's TTS system to avoid double audio streams
"""

import logging
import asyncio
import io
import tempfile
import os
from typing import Optional
import aiohttp

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class SimpleAudioPlayer:
    """Simple audio player that uses the session's TTS system"""

    def __init__(self):
        self.session = None
        self.current_task: Optional[asyncio.Task] = None
        self.is_playing = False
        self.stop_event = asyncio.Event()

    def set_session(self, session):
        """Set the LiveKit agent session"""
        self.session = session
        logger.info("Simple audio player integrated with session")

    def set_context(self, context):
        """Set context (not used in simple player)"""
        pass  # Not needed for simple approach

    async def stop(self):
        """Stop current playback"""
        if self.current_task and not self.current_task.done():
            self.stop_event.set()
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        self.is_playing = False
        logger.info("Audio playback stopped")

    async def play_from_url(self, url: str, title: str = "Audio"):
        """Play audio from URL using TTS system"""
        await self.stop()  # Stop any current playback

        if not self.session:
            logger.error("No session available for audio playback")
            return

        self.is_playing = True
        self.stop_event.clear()
        self.current_task = asyncio.create_task(self._play_audio(url, title))

    async def _play_audio(self, url: str, title: str):
        """Download and play audio through TTS system"""
        try:
            logger.info(f"Starting playback: {title} from {url}")

            # Download audio
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download: HTTP {response.status}")
                        # Use TTS to announce failure
                        if hasattr(self.session, 'tts'):
                            await self.session.tts.say(f"Sorry, couldn't play {title}")
                        return

                    audio_data = await response.read()
                    logger.info(f"Downloaded {len(audio_data)} bytes for {title}")

            if not PYDUB_AVAILABLE:
                # Fallback: just announce what we would play
                logger.warning("Pydub not available, using TTS announcement")
                if hasattr(self.session, 'tts'):
                    await self.session.tts.say(f"Playing {title}")
                return

            # Convert and save as temporary WAV file
            temp_file = None
            try:
                # Convert MP3 to WAV
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))

                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file_path = temp_file.name

                # Export as WAV
                audio_segment.export(temp_file_path, format="wav")
                logger.info(f"Converted audio to WAV: {temp_file_path}")

                # Use TTS to play the WAV file
                if hasattr(self.session, 'tts'):
                    # Try to use the TTS system to play audio file
                    # This is a simplified approach - may need adjustment based on your TTS implementation
                    try:
                        # Some TTS systems can play audio files directly
                        if hasattr(self.session.tts, 'play_audio'):
                            await self.session.tts.play_audio(temp_file_path)
                        else:
                            # Fallback: stream the audio data directly through session
                            await self._stream_via_session(audio_segment, title)
                    except Exception as tts_error:
                        logger.warning(f"TTS playback failed: {tts_error}")
                        # Final fallback: just announce
                        await self.session.tts.say(f"Now playing {title}")

            finally:
                # Clean up temp file
                if temp_file and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

        except asyncio.CancelledError:
            logger.info(f"Playback cancelled: {title}")
            raise
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            # Final fallback
            if hasattr(self.session, 'tts'):
                try:
                    await self.session.tts.say(f"Audio error for {title}")
                except:
                    pass
        finally:
            self.is_playing = False

    async def _stream_via_session(self, audio_segment, title: str):
        """Stream audio directly via session's audio output"""
        try:
            # This is a more direct approach - inject audio into session's pipeline
            if hasattr(self.session, '_output') or hasattr(self.session, 'tts'):
                # Convert to appropriate format
                audio_segment = audio_segment.set_frame_rate(24000)  # Common TTS rate
                audio_segment = audio_segment.set_channels(1)  # Mono

                # Get raw audio data
                raw_audio = audio_segment.raw_data

                logger.info(f"Streaming {len(raw_audio)} bytes of audio for {title}")

                # Try to inject into TTS output stream
                # This might need adjustment based on your specific TTS setup
                if hasattr(self.session, 'tts') and hasattr(self.session.tts, '_synthesize_streamed'):
                    # Some TTS systems allow direct audio injection
                    # This is experimental and may need modification
                    pass

                # Alternative: use session's audio track if available
                await self._inject_into_audio_track(audio_segment, title)

        except Exception as e:
            logger.error(f"Error streaming via session: {e}")

    async def _inject_into_audio_track(self, audio_segment, title: str):
        """Try to inject audio into session's audio track"""
        try:
            # Look for session's audio track
            if hasattr(self.session, '_output_audio_track'):
                track = self.session._output_audio_track
                if track and hasattr(track, 'source'):
                    audio_source = track.source
                    await self._stream_to_source(audio_source, audio_segment, title)
                    return

            # Alternative: look for TTS audio source
            if hasattr(self.session, 'tts') and hasattr(self.session.tts, '_audio_source'):
                audio_source = self.session.tts._audio_source
                await self._stream_to_source(audio_source, audio_segment, title)
                return

            logger.warning("Could not find audio source to inject audio")

        except Exception as e:
            logger.error(f"Error injecting audio: {e}")

    async def _stream_to_source(self, audio_source, audio_segment, title: str):
        """Stream audio data to a specific audio source"""
        try:
            from livekit import rtc

            # Convert to proper format
            audio_segment = audio_segment.set_frame_rate(48000)
            audio_segment = audio_segment.set_channels(1)
            audio_segment = audio_segment.set_sample_width(2)  # 16-bit

            raw_audio = audio_segment.raw_data
            sample_rate = 48000
            frame_duration_ms = 20
            samples_per_frame = sample_rate * frame_duration_ms // 1000
            total_samples = len(raw_audio) // 2
            total_frames = total_samples // samples_per_frame

            logger.info(f"Streaming {total_frames} frames for {title}")

            for frame_num in range(total_frames):
                if self.stop_event.is_set():
                    logger.info("Stopping audio stream")
                    break

                start_byte = frame_num * samples_per_frame * 2
                end_byte = start_byte + (samples_per_frame * 2)
                frame_data = raw_audio[start_byte:end_byte]

                if len(frame_data) < samples_per_frame * 2:
                    frame_data += b'\x00' * (samples_per_frame * 2 - len(frame_data))

                frame = rtc.AudioFrame(
                    data=frame_data,
                    sample_rate=sample_rate,
                    num_channels=1,
                    samples_per_channel=samples_per_frame
                )

                await audio_source.capture_frame(frame)
                await asyncio.sleep(frame_duration_ms / 1000.0)

            logger.info(f"Finished streaming {title}")

        except Exception as e:
            logger.error(f"Error streaming to audio source: {e}")