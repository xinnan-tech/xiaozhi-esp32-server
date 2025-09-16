"""
Story Service Module for LiveKit Agent
Handles story search and playback with AWS CloudFront streaming
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

class StoryService:
    """Service for handling story playback and search"""

    def __init__(self):
        self.metadata = {}
        self.cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN", "dbtnllz9fcr1z.cloudfront.net")
        self.s3_base_url = os.getenv("S3_BASE_URL", "https://cheeko-audio-files.s3.us-east-1.amazonaws.com")
        self.use_cdn = os.getenv("USE_CDN", "true").lower() == "true"
        self.is_initialized = False
        self.semantic_search = SemanticSearchService()

    async def initialize(self) -> bool:
        """Initialize story service by loading metadata"""
        try:
            stories_base_path = Path("src/stories")

            if stories_base_path.exists():
                total_stories = 0
                for category_folder in stories_base_path.iterdir():
                    if category_folder.is_dir():
                        metadata_file = category_folder / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    category_metadata = json.load(f)
                                    self.metadata[category_folder.name] = category_metadata

                                    if isinstance(category_metadata, list):
                                        story_count = len(category_metadata)
                                    else:
                                        story_count = len(category_metadata.get('stories', []))

                                    total_stories += story_count
                                    logger.info(f"Loaded {story_count} stories from {category_folder.name}")
                            except Exception as e:
                                logger.error(f"Error loading metadata from {metadata_file}: {e}")

                logger.info(f"Loaded total of {total_stories} stories from {len(self.metadata)} categories")

                # Initialize semantic search with story metadata
                try:
                    await self.semantic_search.initialize(story_metadata=self.metadata)
                    logger.info("Semantic search initialized for stories")
                except Exception as e:
                    logger.warning(f"Semantic search initialization failed: {e}")

                self.is_initialized = True
                return True
            else:
                logger.warning("Stories folder not found at src/stories")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize story service: {e}")
            return False

    def get_story_url(self, filename: str, category: str = "Adventure") -> str:
        """Generate URL for story file"""
        audio_path = f"stories/{category}/{filename}"
        encoded_path = urllib.parse.quote(audio_path)

        if self.use_cdn and self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{encoded_path}"
        else:
            return f"{self.s3_base_url}/{encoded_path}"

    async def search_stories(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Search for stories using semantic search"""
        if not self.is_initialized:
            return []

        # Use semantic search service
        search_results = await self.semantic_search.search_stories(query, self.metadata, category, limit=5)

        # Convert search results to expected format
        results = []
        for result in search_results:
            results.append({
                'title': result.title,
                'filename': result.filename,
                'category': result.language_or_category,
                'url': self.get_story_url(result.filename, result.language_or_category),
                'score': result.score
            })

        return results

    def get_random_story(self, category: Optional[str] = None) -> Optional[Dict]:
        """Get a random story using semantic search service"""
        if not self.is_initialized or not self.metadata:
            return None

        # Use semantic search service to get random story
        result = self.semantic_search.get_random_item(self.metadata, category)

        if result:
            return {
                'title': result.title,
                'filename': result.filename,
                'category': result.language_or_category,
                'url': self.get_story_url(result.filename, result.language_or_category)
            }

        return None

    def get_all_categories(self) -> List[str]:
        """Get list of all available story categories"""
        return sorted(list(self.metadata.keys()))