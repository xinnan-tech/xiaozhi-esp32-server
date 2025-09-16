"""
Music Service Module for LiveKit Agent
Handles music search and playback with AWS CloudFront streaming
"""

import json
import os
import random
import logging
from typing import Dict, List, Optional
from pathlib import Path
import urllib.parse
from .semantic_search import SemanticSearchService

logger = logging.getLogger(__name__)

class MusicService:
    """Service for handling music playback and search"""

    def __init__(self):
        self.metadata = {}
        self.cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN", "dbtnllz9fcr1z.cloudfront.net")
        self.s3_base_url = os.getenv("S3_BASE_URL", "https://cheeko-audio-files.s3.us-east-1.amazonaws.com")
        self.use_cdn = os.getenv("USE_CDN", "true").lower() == "true"
        self.is_initialized = False
        self.semantic_search = SemanticSearchService()

    async def initialize(self) -> bool:
        """Initialize music service by loading metadata"""
        try:
            music_base_path = Path("src/music")

            if music_base_path.exists():
                total_songs = 0
                for language_folder in music_base_path.iterdir():
                    if language_folder.is_dir():
                        metadata_file = language_folder / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    language_metadata = json.load(f)
                                    self.metadata[language_folder.name] = language_metadata

                                    song_count = len(language_metadata)
                                    total_songs += song_count
                                    logger.info(f"Loaded {song_count} songs from {language_folder.name}")
                            except Exception as e:
                                logger.error(f"Error loading metadata from {metadata_file}: {e}")

                logger.info(f"Loaded total of {total_songs} songs from {len(self.metadata)} languages")

                # Initialize semantic search with music metadata
                try:
                    await self.semantic_search.initialize(music_metadata=self.metadata)
                    logger.info("Semantic search initialized for music")
                except Exception as e:
                    logger.warning(f"Semantic search initialization failed: {e}")

                self.is_initialized = True
                return True
            else:
                logger.warning("Music folder not found at src/music")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize music service: {e}")
            return False

    def get_song_url(self, filename: str, language: str = "English") -> str:
        """Generate URL for song file"""
        audio_path = f"music/{language}/{filename}"
        encoded_path = urllib.parse.quote(audio_path)

        if self.use_cdn and self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{encoded_path}"
        else:
            return f"{self.s3_base_url}/{encoded_path}"

    async def search_songs(self, query: str, language: Optional[str] = None) -> List[Dict]:
        """Search for songs using semantic search"""
        if not self.is_initialized:
            return []

        # Use semantic search service
        search_results = await self.semantic_search.search_music(query, self.metadata, language, limit=5)

        # Convert search results to expected format
        results = []
        for result in search_results:
            results.append({
                'title': result.title,
                'filename': result.filename,
                'language': result.language_or_category,
                'url': self.get_song_url(result.filename, result.language_or_category),
                'score': result.score
            })

        return results

    def get_random_song(self, language: Optional[str] = None) -> Optional[Dict]:
        """Get a random song using semantic search service"""
        if not self.is_initialized or not self.metadata:
            return None

        # Use semantic search service to get random song
        result = self.semantic_search.get_random_item(self.metadata, language)

        if result:
            return {
                'title': result.title,
                'filename': result.filename,
                'language': result.language_or_category,
                'url': self.get_song_url(result.filename, result.language_or_category)
            }

        return None

    def get_all_languages(self) -> List[str]:
        """Get list of all available music languages"""
        return sorted(list(self.metadata.keys()))