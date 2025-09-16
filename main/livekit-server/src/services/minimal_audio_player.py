"""
Minimal Audio Player for LiveKit Agent
Creates a separate audio track for music/stories
"""

import logging
import asyncio
import io
from typing import Optional
import aiohttp
from livekit import rtc

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class MinimalAudioPlayer:
    """Minimal audio player that creates its own audio track"""

    def __init__(self):
        self.room = None
        self.audio_source = None
        self.audio_track = None
        self.current_task: Optional[asyncio.Task] = None
        self.is_playing = False
        self.stop_event = asyncio.Event()

    def set_session(self, session):
        """Extract room from session"""
        pass  # Not needed for minimal approach

    def set_context(self, context):
        """Set the job context to get room access"""
        if context and hasattr(context, 'room'):
            self.room = context.room
            logger.info(f"Minimal audio player got room: {self.room}")
        else:
            logger.error("No room available in context")

    async def initialize_audio_track(self):
        """Initialize the audio track for music playback"""
        if not self.room:
            logger.error("No room available for audio track")
            return False

        try:
            # Create audio source
            self.audio_source = rtc.AudioSource(48000, 1)  # 48kHz, mono

            # Create audio track
            self.audio_track = rtc.LocalAudioTrack.create_audio_track("music", self.audio_source)

            # Publish the track
            publication = await self.room.local_participant.publish_track(self.audio_track)

            logger.info(f"Audio track published successfully: {publication.sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize audio track: {e}")
            return False

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
        """Play audio from URL"""
        # Ensure audio source is ready
        if not self.audio_source:
            logger.info("Initializing audio track for first playback...")
            if not await self.initialize_audio_track():
                logger.error("Cannot play audio - failed to initialize audio track")
                return

        # Verify audio source is still valid
        if not self.audio_source:
            logger.error("Audio source is None after initialization")
            return

        await self.stop()  # Stop any current playback

        logger.info(f"Starting audio playback task for: {title}")
        self.is_playing = True
        self.stop_event.clear()

        # Start playback in background task
        self.current_task = asyncio.create_task(self._play_audio(url, title))

    async def _play_audio(self, url: str, title: str):
        """Download and play audio"""
        try:
            logger.info(f"Starting playback: {title} from {url}")

            # Download audio with timeout
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download: HTTP {response.status}")
                        return

                    audio_data = await response.read()
                    logger.info(f"Downloaded {len(audio_data)} bytes for {title}")

            if not PYDUB_AVAILABLE:
                logger.error("Pydub not available - cannot play audio")
                return

            # Convert and stream
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
            await self._stream_audio(audio_segment, title)

        except asyncio.CancelledError:
            logger.info(f"Playback cancelled: {title}")
            raise
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
        finally:
            self.is_playing = False

    async def _stream_audio(self, audio_segment, title: str):
        """Stream audio to the audio source"""
        try:
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

            # Stream in smaller chunks to prevent blocking
            chunk_size = 50  # Process 50 frames at a time
            frames_processed = 0

            for chunk_start in range(0, total_frames, chunk_size):
                if self.stop_event.is_set():
                    logger.info("Stopping audio stream")
                    break

                chunk_end = min(chunk_start + chunk_size, total_frames)

                # Process chunk of frames
                for frame_num in range(chunk_start, chunk_end):
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

                    try:
                        await self.audio_source.capture_frame(frame)
                    except Exception as frame_error:
                        logger.warning(f"Frame capture error: {frame_error}")
                        # Continue with next frame

                    frames_processed += 1

                    # Small delay between frames
                    await asyncio.sleep(frame_duration_ms / 1000.0)

                # Yield control after each chunk to prevent blocking
                await asyncio.sleep(0.001)  # 1ms yield

                # Log progress every 10 chunks
                if (chunk_start // chunk_size) % 10 == 0:
                    progress = (frames_processed / total_frames) * 100
                    logger.debug(f"Streaming progress: {progress:.1f}% ({frames_processed}/{total_frames} frames)")

            logger.info(f"Finished streaming {title} - {frames_processed} frames processed")

        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            # Don't re-raise to prevent blocking the event loop