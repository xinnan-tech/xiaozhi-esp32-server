"""
Audio Player Module for LiveKit Agent
Handles audio streaming by coordinating with the session's TTS
"""

import logging
import asyncio
import io
from typing import Optional
import aiohttp

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class AudioPlayer:
    """Handles audio playback by coordinating with LiveKit session"""

    def __init__(self):
        self.session = None
        self.context = None
        self.current_task: Optional[asyncio.Task] = None
        self.is_playing = False
        self.stop_event = asyncio.Event()

    def set_session(self, session):
        """Set the LiveKit agent session for audio coordination"""
        self.session = session
        logger.info("Audio player integrated with agent session")

    def set_context(self, context):
        """Set the LiveKit job context for room access"""
        self.context = context
        logger.info("Audio player integrated with job context")

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
        """Play audio from URL using session's TTS system"""
        await self.stop()  # Stop any current playback

        if not self.session:
            logger.error("No session available for audio playback")
            return

        self.is_playing = True
        self.stop_event.clear()

        # Use the session's TTS to speak a placeholder while we prepare the audio
        # Then replace it with the actual audio content
        self.current_task = asyncio.create_task(self._play_through_tts(url, title))

    async def _play_through_tts(self, url: str, title: str):
        """Play audio by routing through the session's TTS system"""
        try:
            logger.info(f"Starting playback: {title} from {url}")

            # Download audio data
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download audio: HTTP {response.status}")
                        # Fallback: use TTS to announce the issue
                        if self.session and self.session.tts:
                            await self.session.tts.say(f"Sorry, I couldn't play {title}")
                        return

                    audio_data = await response.read()
                    logger.info(f"Downloaded {len(audio_data)} bytes for {title}")

            # Process the audio and create a temporary audio file URL or use TTS synthesis
            # For now, we'll use a simpler approach: let TTS handle the audio
            if PYDUB_AVAILABLE:
                await self._stream_through_session(audio_data, title)
            else:
                # Fallback: just announce what we're playing
                if self.session and self.session.tts:
                    await self.session.tts.say(f"Now playing {title}")

        except asyncio.CancelledError:
            logger.info(f"Playback cancelled: {title}")
            raise
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            # Fallback: use TTS to announce error
            if self.session and self.session.tts:
                await self.session.tts.say("Sorry, there was an error playing the audio")
        finally:
            self.is_playing = False

    async def _stream_through_session(self, audio_data: bytes, title: str):
        """Stream audio data through the session's audio pipeline"""
        try:
            # Convert audio to proper format
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))

            # Try to get the room from context first, then session
            room = None
            if self.context and hasattr(self.context, 'room'):
                room = self.context.room
                logger.info(f"Got room from context: {room}")
            elif hasattr(self.session, '_session') and hasattr(self.session._session, 'room'):
                room = self.session._session.room
            elif hasattr(self.session, 'room'):
                room = self.session.room
            elif hasattr(self.session, '_ctx') and hasattr(self.session._ctx, 'room'):
                room = self.session._ctx.room

            if room:
                logger.info(f"Found room: {room}, streaming audio directly")

                # Create audio source for music
                from livekit import rtc
                audio_source = rtc.AudioSource(48000, 1)

                # Create and publish audio track
                track = rtc.LocalAudioTrack.create_audio_track("music", audio_source)
                publication = await room.local_participant.publish_track(track)

                try:
                    # Stream the audio
                    await self._stream_audio_data(audio_source, audio_segment, title)
                finally:
                    # Cleanup
                    try:
                        await room.local_participant.unpublish_track(publication.sid)
                    except Exception as cleanup_error:
                        logger.warning(f"Error cleaning up audio track: {cleanup_error}")

            else:
                # Fallback: try to use session's TTS system to play audio
                logger.warning("No room found, attempting TTS fallback")
                if hasattr(self.session, 'tts') and self.session.tts:
                    # Convert audio to text announcement as fallback
                    await self.session.tts.say(f"Now playing {title}")
                else:
                    logger.error("No TTS available for audio playback")

            logger.info(f"Finished streaming {title}")

        except Exception as e:
            logger.error(f"Error streaming through session: {e}")
            # Final fallback to TTS announcement
            try:
                if hasattr(self.session, 'tts') and self.session.tts:
                    await self.session.tts.say(f"Unable to play {title}, but I found it")
            except Exception as tts_error:
                logger.error(f"Even TTS fallback failed: {tts_error}")

    async def _stream_audio_data(self, audio_source, audio_segment, title: str):
        """Stream audio segment data to the audio source"""
        # Convert to required format
        audio_segment = audio_segment.set_frame_rate(48000)
        audio_segment = audio_segment.set_channels(1)
        audio_segment = audio_segment.set_sample_width(2)

        raw_audio = audio_segment.raw_data
        sample_rate = 48000
        frame_duration_ms = 20
        samples_per_frame = sample_rate * frame_duration_ms // 1000
        total_samples = len(raw_audio) // 2
        total_frames = total_samples // samples_per_frame

        logger.info(f"Streaming {total_frames} frames for {title}")

        from livekit import rtc

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