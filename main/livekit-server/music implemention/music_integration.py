"""
Music Integration Module for LiveKit Agent
Combines semantic search with AWS CloudFront streaming
"""

import json
import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from pathlib import Path
import threading
import queue
import io
import urllib.parse

from semantic import SemanticMusicSearch, MusicSearchResult
from livekit import rtc
import aiohttp
import wave

try:
    from pydub import AudioSegment
    from pydub.utils import which
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

class MusicPlayer:
    """Music player for LiveKit agent with semantic search capabilities"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.semantic_search = None
        self.current_track = None
        self.is_playing = False
        self.is_paused = False

        # AWS/CDN Configuration
        self.cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN", "dbtnllz9fcr1z.cloudfront.net")
        self.s3_base_url = os.getenv("S3_BASE_URL", "https://cheeko-audio-files.s3.us-east-1.amazonaws.com")
        self.use_cdn = os.getenv("USE_CDN", "true").lower() == "true"

        # Music metadata (organized by language)
        self.metadata = {}
        # Story metadata (organized by category/genre)
        self.story_metadata = {}
        self.is_initialized = False

        # Filename fixes for CloudFront compatibility
        self.filename_fixes = {
            "Head, Shoulders, Knees and Toes.mp3": "Head Shoulders Knees and Toes.mp3",
            "I'm A Little Teapot.mp3": "Im A Little Teapot.mp3",
            "Rain rain go away.mp3": "Rain Rain Go Away.mp3"
        }

        # Audio streaming components
        self.audio_source = None
        self.current_audio_task = None
        self.audio_queue = queue.Queue()
        self.stop_streaming = threading.Event()

    async def initialize(self) -> bool:
        """Initialize the music player with semantic search and metadata"""
        try:
            # Load music metadata from multiple language folders
            self.metadata = {}
            music_base_path = Path("music")
            
            if music_base_path.exists():
                total_songs = 0
                # Look for metadata.json files in each language subfolder
                for language_folder in music_base_path.iterdir():
                    if language_folder.is_dir():
                        metadata_file = language_folder / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    language_metadata = json.load(f)
                                    self.metadata[language_folder.name] = language_metadata
                                    song_count = len(language_metadata) if isinstance(language_metadata, list) else len(language_metadata.get('songs', language_metadata))
                                    total_songs += song_count
                                    self.logger.info(f"Loaded {song_count} songs from music/{language_folder.name}/metadata.json")
                            except Exception as e:
                                self.logger.error(f"Error loading music metadata from {metadata_file}: {e}")
                        else:
                            self.logger.warning(f"No metadata.json found in music/{language_folder.name}")
                
                self.logger.info(f"Loaded total of {total_songs} songs from {len(self.metadata)} languages")
            else:
                self.logger.warning("music folder not found")
            
            # Load story metadata from multiple category folders
            self.story_metadata = {}
            stories_base_path = Path("stories")
            
            if stories_base_path.exists():
                total_stories = 0
                # Look for metadata.json files in each category subfolder
                for category_folder in stories_base_path.iterdir():
                    if category_folder.is_dir():
                        metadata_file = category_folder / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    category_metadata = json.load(f)
                                    self.story_metadata[category_folder.name] = category_metadata
                                    story_count = len(category_metadata) if isinstance(category_metadata, list) else len(category_metadata.get('stories', category_metadata))
                                    total_stories += story_count
                                    self.logger.info(f"Loaded {story_count} stories from stories/{category_folder.name}/metadata.json")
                            except Exception as e:
                                self.logger.error(f"Error loading story metadata from {metadata_file}: {e}")
                        else:
                            self.logger.warning(f"No metadata.json found in stories/{category_folder.name}")
                
                self.logger.info(f"Loaded total of {total_stories} stories from {len(self.story_metadata)} categories")
            else:
                self.logger.warning("stories folder not found")
            
            # Check if we have any content
            if len(self.metadata) == 0 and len(self.story_metadata) == 0:
                self.logger.error("No metadata files found for music or stories")
                return False

            # Initialize semantic search for music
            self.semantic_search = SemanticMusicSearch({
                "qdrant_url": "https://a2482b9f-2c29-476e-9ff0-741aaaaf632e.eu-west-1-0.aws.cloud.qdrant.io",
                "qdrant_api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zPBGAqVGy-edbbgfNOJsPWV496BsnQ4ELOFvsLNyjsk",
                "collection_name": "xiaozhi_music",  # Music has its own collection
                "search_limit": 5,
                "min_score_threshold": 0.3
            })

            if not self.semantic_search.initialize():
                self.logger.error("Failed to initialize semantic search")
                return False

            self.is_initialized = True
            self.logger.info("Music player initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize music player: {e}")
            return False

    def get_language_metadata(self, language: str) -> Dict[str, Any]:
        """Get music metadata for a specific language"""
        return self.metadata.get(language, {})
    
    def get_story_category_metadata(self, category: str) -> Dict[str, Any]:
        """Get story metadata for a specific category"""
        return self.story_metadata.get(category, {})
    
    def get_all_languages(self) -> List[str]:
        """Get list of all available music languages"""
        return sorted(list(self.metadata.keys()))
    
    def get_music_languages(self) -> List[str]:
        """Get list of languages with music content"""
        return list(self.metadata.keys())
    
    def get_story_categories(self) -> List[str]:
        """Get list of available story categories"""
        return list(self.story_metadata.keys())
    
    def get_all_story_categories(self) -> List[str]:
        """Get list of all available story categories (sorted)"""
        return sorted(list(self.story_metadata.keys()))
    
    def get_song_url(self, filename: str, language: str = "English") -> str:
        """Generate URL for song file using your CDN structure"""
        # Your structure: music/{language}/{filename}
        audio_path = f"music/{language}/{filename}"
        encoded_path = urllib.parse.quote(audio_path)

        if self.use_cdn and self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{encoded_path}"
        else:
            return f"{self.s3_base_url}/{encoded_path}"

    def get_story_url(self, filename: str, category: str = "Adventure") -> str:
        """Generate URL for story file using your CDN structure"""
        # Structure: stories/{category}/{filename}
        audio_path = f"stories/{category}/{filename}"
        encoded_path = urllib.parse.quote(audio_path)

        if self.use_cdn and self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{encoded_path}"
        else:
            return f"{self.s3_base_url}/{encoded_path}"

    def get_alternative_story_urls(self, filename: str, category: str = "Adventure") -> list:
        """Get multiple URL attempts for a story file"""
        urls = []

        # Primary path: stories/{category}/{filename}
        primary_paths = [
            f"stories/{category}/{filename}",
            f"stories/{category.title()}/{filename}",  # Try title case
            f"stories/{category.lower()}/{filename}",  # Try lowercase
        ]

        # Add each path for both CloudFront and S3
        for path in primary_paths:
            encoded_path = urllib.parse.quote(path)

            if self.cloudfront_domain:
                urls.append(f"https://{self.cloudfront_domain}/{encoded_path}")

            if self.s3_base_url:
                urls.append(f"{self.s3_base_url}/{encoded_path}")

        # Fallback: try direct filename (legacy)
        encoded_filename = urllib.parse.quote(filename)
        if self.cloudfront_domain:
            urls.append(f"https://{self.cloudfront_domain}/{encoded_filename}")
        if self.s3_base_url:
            urls.append(f"{self.s3_base_url}/{encoded_filename}")

        return urls

    def get_alternative_urls(self, filename: str, language: str = "English") -> list:
        """Get multiple URL attempts for a file based on your reference code structure"""
        urls = []

        # Primary path based on your reference code: music/{language}/{filename}
        primary_paths = [
            f"music/{language}/{filename}",
            f"music/{language.title()}/{filename}",  # Try capitalized language
            f"music/{language.lower()}/{filename}",  # Try lowercase language
        ]

        # Add each path for both CloudFront and S3
        for path in primary_paths:
            encoded_path = urllib.parse.quote(path)

            if self.cloudfront_domain:
                urls.append(f"https://{self.cloudfront_domain}/{encoded_path}")

            if self.s3_base_url:
                urls.append(f"{self.s3_base_url}/{encoded_path}")

        # Fallback: try direct filename (legacy)
        encoded_filename = urllib.parse.quote(filename)
        if self.cloudfront_domain:
            urls.append(f"https://{self.cloudfront_domain}/{encoded_filename}")
        if self.s3_base_url:
            urls.append(f"{self.s3_base_url}/{encoded_filename}")

        return urls

    async def search_stories_by_category(self, query: str, category: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for stories, optionally filtered by category"""
        if not self.is_initialized:
            return []

        try:
            # Get all results first
            results = self.semantic_search.search(query, limit=limit * 2)  # Get more to filter

            # Convert to dict format for stories
            formatted_results = []
            for result in results:
                # Determine category from metadata or file path
                result_category = result.metadata.get("category", "Adventure")
                
                # Filter by category if specified
                if category and result_category.lower() != category.lower():
                    continue
                
                story_data = {
                    "title": result.title,
                    "romanized": result.romanized,
                    "alternatives": result.alternatives,
                    "score": result.score,
                    "filename": result.metadata.get("filename", f"{result.title}.mp3"),
                    "category": result_category,
                    "url": self.get_story_url(result.metadata.get("filename", f"{result.title}.mp3"), result_category),
                    "file_path": result.file_path,
                    "type": "story"
                }
                formatted_results.append(story_data)
                
                # Stop when we have enough results
                if len(formatted_results) >= limit:
                    break

            return formatted_results

        except Exception as e:
            self.logger.error(f"Story search failed: {e}")
            return []

    async def search_stories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for stories using semantic search (all categories)"""
        return await self.search_stories_by_category(query, category=None, limit=limit)

    async def find_best_story_match(self, query: str, category: str = None) -> Optional[Dict[str, Any]]:
        """Find the best matching story for a query, optionally in a specific category"""
        results = await self.search_stories_by_category(query, category=category, limit=1)
        return results[0] if results else None

    async def search_music(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for music using semantic search"""
        if not self.is_initialized:
            return []

        try:
            results = self.semantic_search.search(query, limit=limit)

            # Convert to dict format for easy serialization
            formatted_results = []
            for result in results:
                song_data = {
                    "title": result.title,
                    "romanized": result.romanized,
                    "alternatives": result.alternatives,
                    "score": result.score,
                    "filename": result.metadata.get("filename", f"{result.title}.mp3"),
                    "url": self.get_song_url(result.metadata.get("filename", f"{result.title}.mp3")),
                    "file_path": result.file_path,
                    "type": "music"
                }
                formatted_results.append(song_data)

            return formatted_results

        except Exception as e:
            self.logger.error(f"Music search failed: {e}")
            return []

    async def find_best_match(self, query: str) -> Optional[Dict[str, Any]]:
        """Find the best matching song for a query"""
        results = await self.search_music(query, limit=1)
        return results[0] if results else None

    def set_audio_source(self, audio_source: rtc.AudioSource):
        """Set the LiveKit audio source for streaming"""
        self.audio_source = audio_source

    async def download_and_stream_audio(self, url: str, song_title: str):
        """Download MP3 from URL and stream to LiveKit audio source"""
        try:
            self.logger.info(f"Starting download for: {song_title}")
            self.stop_streaming.clear()

            # Get the filename and language from the current track
            filename = self.current_track.get('filename', f"{song_title}.mp3") if self.current_track else f"{song_title}.mp3"
            language = self.current_track.get('language', 'English') if self.current_track else 'English'

            # Try multiple URLs with the correct language
            urls_to_try = self.get_alternative_urls(filename, language)
            self.logger.info(f"Will try {len(urls_to_try)} URLs for {song_title} in {language} folder")

            async with aiohttp.ClientSession() as session:
                for attempt, test_url in enumerate(urls_to_try, 1):
                    self.logger.info(f"Attempt {attempt}/{len(urls_to_try)}: {test_url}")

                    try:
                        async with session.get(test_url) as response:
                            self.logger.info(f"HTTP Response: {response.status} for attempt {attempt}")

                            if response.status == 200:
                                # Success! Read the MP3 data
                                mp3_data = await response.read()
                                self.logger.info(f"✅ Downloaded {len(mp3_data)} bytes for {song_title} from attempt {attempt}")

                                # Stream the actual audio data
                                await self.stream_audio_data(mp3_data, song_title)
                                return  # Success, exit the function

                            elif response.status == 403:
                                self.logger.warning(f"❌ Access denied (403) for attempt {attempt}")
                            elif response.status == 404:
                                self.logger.warning(f"❌ Not found (404) for attempt {attempt}")
                            else:
                                self.logger.warning(f"❌ HTTP {response.status} for attempt {attempt}")

                    except Exception as url_error:
                        self.logger.warning(f"❌ Error with attempt {attempt}: {url_error}")

                # All URLs failed
                self.logger.error(f"❌ All {len(urls_to_try)} URLs failed for {song_title}")
                self.logger.info("🔇 Streaming silence as fallback...")
                await self._stream_silence(song_title, 30)

        except Exception as e:
            self.logger.error(f"Error downloading/streaming {song_title}: {e}")
            # Stream silence as fallback
            await self._stream_silence(song_title, 30)

    async def stream_audio_data(self, audio_data: bytes, song_title: str):
        """Stream audio data to LiveKit"""
        try:
            if not self.audio_source:
                self.logger.error("❌ No audio source available for streaming - music will not play!")
                return
            else:
                self.logger.info(f"✅ Audio source available: {type(self.audio_source)} for {song_title}")

            sample_rate = 48000
            channels = 1
            frame_duration_ms = 20  # 20ms frames
            samples_per_frame = sample_rate * frame_duration_ms // 1000

            if PYDUB_AVAILABLE:
                self.logger.info(f"Decoding MP3 for {song_title} using pydub")
                try:
                    # Load MP3 data using pydub
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))

                    # Convert to the format we need
                    audio_segment = audio_segment.set_frame_rate(sample_rate)
                    audio_segment = audio_segment.set_channels(channels)
                    audio_segment = audio_segment.set_sample_width(2)  # 16-bit

                    # Get raw audio data
                    raw_audio = audio_segment.raw_data
                    total_samples = len(raw_audio) // 2  # 16-bit samples
                    total_frames = total_samples // samples_per_frame

                    self.logger.info(f"Streaming {total_frames} frames for {song_title} ({len(raw_audio)} bytes)")

                    # Stream the actual audio data
                    audio_started = False
                    silent_frame_count = 0
                    max_leading_silence_frames = 250  # Skip up to 5 seconds of silence at start (250 * 20ms = 5000ms)

                    for frame_num in range(total_frames):
                        if self.stop_streaming.is_set() or not self.is_playing:
                            self.logger.info("Stopping audio stream")
                            break

                        if self.is_paused:
                            await asyncio.sleep(frame_duration_ms / 1000.0)
                            continue

                        # Extract frame data
                        start_byte = frame_num * samples_per_frame * 2
                        end_byte = start_byte + (samples_per_frame * 2)
                        frame_data = raw_audio[start_byte:end_byte]

                        # Pad if necessary
                        if len(frame_data) < samples_per_frame * 2:
                            frame_data += b'\x00' * (samples_per_frame * 2 - len(frame_data))

                        # Check if this frame has audio content (skip leading silence)
                        non_zero_bytes = sum(1 for b in frame_data if b != 0)
                        is_silent = non_zero_bytes < (len(frame_data) * 0.01)  # Less than 1% non-zero = silence

                        if not audio_started and is_silent:
                            silent_frame_count += 1
                            if silent_frame_count <= max_leading_silence_frames:
                                # Skip this silent frame at the beginning
                                continue
                            else:
                                # Too much silence, just play it anyway
                                if silent_frame_count == max_leading_silence_frames + 1:
                                    self.logger.info(f"Skipping {silent_frame_count} leading silent frames, now playing audio...")
                                audio_started = True
                        elif not audio_started and not is_silent:
                            # Found first audio content
                            audio_started = True
                            if silent_frame_count > 0:
                                self.logger.info(f"Skipped {silent_frame_count} silent frames at start, audio content begins now")

                        # Create LiveKit audio frame
                        frame = rtc.AudioFrame(
                            data=frame_data,
                            sample_rate=sample_rate,
                            num_channels=channels,
                            samples_per_channel=samples_per_frame
                        )

                        # Send frame to LiveKit
                        try:
                            await self.audio_source.capture_frame(frame)
                        except Exception as frame_error:
                            self.logger.error(f"❌ Failed to capture audio frame {frame_num}: {frame_error}")
                            # Continue with next frame instead of stopping completely

                        # Wait for next frame
                        await asyncio.sleep(frame_duration_ms / 1000.0)

                    self.logger.info(f"Finished streaming {song_title}")

                except Exception as e:
                    self.logger.error(f"Error decoding MP3: {e}")
                    # Fallback to silence
                    await self._stream_silence(song_title, 30)  # 30 seconds of silence

            else:
                self.logger.warning("Pydub not available - streaming silence as placeholder")
                await self._stream_silence(song_title, 30)  # 30 seconds of silence

        except Exception as e:
            self.logger.error(f"Error streaming audio data: {e}")

    async def _stream_silence(self, song_title: str, duration_seconds: int):
        """Stream silence as a fallback"""
        sample_rate = 48000
        channels = 1
        frame_duration_ms = 20
        samples_per_frame = sample_rate * frame_duration_ms // 1000
        total_frames = duration_seconds * 1000 // frame_duration_ms

        self.logger.info(f"Streaming {duration_seconds}s of silence for {song_title}")

        for frame_num in range(total_frames):
            if self.stop_streaming.is_set() or not self.is_playing:
                break

            if self.is_paused:
                await asyncio.sleep(frame_duration_ms / 1000.0)
                continue

            # Create silent audio frame
            audio_frame_data = b'\x00' * (samples_per_frame * 2)

            frame = rtc.AudioFrame(
                data=audio_frame_data,
                sample_rate=sample_rate,
                num_channels=channels,
                samples_per_channel=samples_per_frame
            )

            await self.audio_source.capture_frame(frame)
            await asyncio.sleep(frame_duration_ms / 1000.0)

    async def play_story(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Play a specific story by streaming it through LiveKit"""
        try:
            # Stop any currently playing content
            if self.current_audio_task and not self.current_audio_task.done():
                self.stop_streaming.set()
                self.current_audio_task.cancel()

            self.current_track = story_data
            self.is_playing = True
            self.is_paused = False

            self.logger.info(f"Playing story: {story_data['title']} - {story_data['url']}")

            # Start streaming the audio
            if self.audio_source:
                self.current_audio_task = asyncio.create_task(
                    self.download_and_stream_story(story_data['url'], story_data['title'])
                )
                self.logger.info("Story streaming task started")
            else:
                self.logger.warning("No audio source available - story info returned without playback")

            return {
                "status": "success",
                "action": "play",
                "story": {
                    "title": story_data["title"],
                    "url": story_data["url"],
                    "filename": story_data["filename"]
                },
                "message": f"Now playing story: {story_data['title']}"
            }

        except Exception as e:
            self.logger.error(f"Failed to play story: {e}")
            return {
                "status": "error",
                "message": f"Failed to play story: {str(e)}"
            }

    async def download_and_stream_story(self, url: str, story_title: str):
        """Download story MP3 from URL and stream to LiveKit audio source"""
        try:
            self.logger.info(f"Starting download for story: {story_title}")
            self.stop_streaming.clear()

            # Get the filename from the current track
            filename = self.current_track.get('filename', f"{story_title}.mp3") if self.current_track else f"{story_title}.mp3"

            # Try multiple URLs for stories
            urls_to_try = self.get_alternative_story_urls(filename)
            self.logger.info(f"Will try {len(urls_to_try)} URLs for story {story_title}")

            async with aiohttp.ClientSession() as session:
                for attempt, test_url in enumerate(urls_to_try, 1):
                    self.logger.info(f"Attempt {attempt}/{len(urls_to_try)}: {test_url}")

                    try:
                        async with session.get(test_url) as response:
                            self.logger.info(f"HTTP Response: {response.status} for attempt {attempt}")

                            if response.status == 200:
                                # Success! Read the MP3 data
                                mp3_data = await response.read()
                                self.logger.info(f"✅ Downloaded {len(mp3_data)} bytes for story {story_title} from attempt {attempt}")

                                # Stream the actual audio data
                                await self.stream_audio_data(mp3_data, story_title)
                                return  # Success, exit the function

                            elif response.status == 403:
                                self.logger.warning(f"❌ Access denied (403) for attempt {attempt}")
                            elif response.status == 404:
                                self.logger.warning(f"❌ Not found (404) for attempt {attempt}")
                            else:
                                self.logger.warning(f"❌ HTTP {response.status} for attempt {attempt}")

                    except Exception as url_error:
                        self.logger.warning(f"❌ Error with attempt {attempt}: {url_error}")

                # All URLs failed
                self.logger.error(f"❌ All {len(urls_to_try)} URLs failed for story {story_title}")
                self.logger.info("🔇 Streaming silence as fallback...")
                await self._stream_silence(story_title, 30)

        except Exception as e:
            self.logger.error(f"Error downloading/streaming story {story_title}: {e}")
            # Stream silence as fallback
            await self._stream_silence(story_title, 30)

    async def play_song(self, song_data: Dict[str, Any]) -> Dict[str, Any]:
        """Play a specific song by streaming it through LiveKit"""
        try:
            # Stop any currently playing song
            if self.current_audio_task and not self.current_audio_task.done():
                self.stop_streaming.set()
                self.current_audio_task.cancel()

            self.current_track = song_data
            self.is_playing = True
            self.is_paused = False

            self.logger.info(f"Playing: {song_data['title']} - {song_data['url']}")

            # Start streaming the audio
            if self.audio_source:
                self.current_audio_task = asyncio.create_task(
                    self.download_and_stream_audio(song_data['url'], song_data['title'])
                )
                self.logger.info("Audio streaming task started")
            else:
                self.logger.warning("No audio source available - song info returned without playback")

            return {
                "status": "success",
                "action": "play",
                "song": {
                    "title": song_data["title"],
                    "url": song_data["url"],
                    "filename": song_data["filename"]
                },
                "message": f"Now playing: {song_data['title']}"
            }

        except Exception as e:
            self.logger.error(f"Failed to play song: {e}")
            return {
                "status": "error",
                "message": f"Failed to play song: {str(e)}"
            }

    async def pause_music(self) -> Dict[str, Any]:
        """Pause current music"""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            return {
                "status": "success",
                "action": "pause",
                "message": "Music paused"
            }
        else:
            return {
                "status": "info",
                "message": "No music is currently playing"
            }

    async def resume_music(self) -> Dict[str, Any]:
        """Resume paused music"""
        if self.is_paused and self.current_track:
            self.is_paused = False
            return {
                "status": "success",
                "action": "resume",
                "message": f"Resumed: {self.current_track['title']}"
            }
        else:
            return {
                "status": "info",
                "message": "No music to resume"
            }

    async def stop_music(self) -> Dict[str, Any]:
        """Stop current music"""
        if self.is_playing or self.is_paused:
            self.is_playing = False
            self.is_paused = False
            self.stop_streaming.set()

            # Cancel the current audio task
            if self.current_audio_task and not self.current_audio_task.done():
                self.current_audio_task.cancel()

            current_title = self.current_track["title"] if self.current_track else "Unknown"
            self.current_track = None

            return {
                "status": "success",
                "action": "stop",
                "message": f"Stopped: {current_title}"
            }
        else:
            return {
                "status": "info",
                "message": "No music is currently playing"
            }

    def get_current_status(self) -> Dict[str, Any]:
        """Get current music/story player status"""
        # Calculate total songs across all languages
        total_songs = 0
        for language_metadata in self.metadata.values():
            if isinstance(language_metadata, list):
                total_songs += len(language_metadata)
            else:
                total_songs += len(language_metadata.get('songs', language_metadata))
        
        # Calculate total stories across all languages
        total_stories = 0
        for language_metadata in self.story_metadata.values():
            if isinstance(language_metadata, list):
                total_stories += len(language_metadata)
            else:
                total_stories += len(language_metadata.get('stories', language_metadata))
        
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_track": self.current_track,
            "total_songs": total_songs,
            "total_stories": total_stories,
            "music_languages": list(self.metadata.keys()),
            "story_languages": list(self.story_metadata.keys()),
            "all_languages": self.get_all_languages()
        }

# Global music player instance
music_player = MusicPlayer()