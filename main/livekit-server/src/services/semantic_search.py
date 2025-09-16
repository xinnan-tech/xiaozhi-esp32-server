"""
Semantic Search Module for Music and Stories
Enhanced version with Qdrant integration
"""

import logging
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from .qdrant_semantic_search import QdrantSemanticSearch, QDRANT_AVAILABLE

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results"""
    title: str
    filename: str
    language_or_category: str
    score: float
    metadata: Dict

class SemanticSearchService:
    """
    Semantic search service for music and stories
    Uses Qdrant when available, falls back to text matching otherwise
    """

    def __init__(self):
        self.qdrant_search = QdrantSemanticSearch() if QDRANT_AVAILABLE else None
        self.is_qdrant_initialized = False
        self.logger = logger

        if not QDRANT_AVAILABLE:
            self.logger.warning("Qdrant not available, using fallback text search")

    async def initialize(self, music_metadata: Dict = None, story_metadata: Dict = None) -> bool:
        """Initialize Qdrant search - skip indexing, use existing cloud collections"""
        if not self.qdrant_search:
            return False

        try:
            # Initialize Qdrant connection only
            initialized = await self.qdrant_search.initialize()
            if not initialized:
                return False

            # Skip indexing - use existing cloud collections
            self.logger.info("Using existing Qdrant cloud collections (skipping indexing)")

            self.is_qdrant_initialized = True
            self.logger.info("Qdrant semantic search initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant search: {e}")
            return False

    async def search_music(self, query: str, music_metadata: Dict, language: Optional[str] = None, limit: int = 5) -> List[SearchResult]:
        """Search for music using Qdrant or fallback to text search"""
        if self.is_qdrant_initialized:
            try:
                qdrant_results = await self.qdrant_search.search_music(query, language, limit)
                # Convert to SearchResult format
                results = []
                for result in qdrant_results:
                    results.append(SearchResult(
                        title=result.title,
                        filename=result.filename,
                        language_or_category=result.language_or_category,
                        score=result.score,
                        metadata=result.metadata
                    ))
                return results
            except Exception as e:
                self.logger.warning(f"Qdrant search failed, using fallback: {e}")

        # Fallback to text search
        return self._search_content(query, music_metadata, content_type="music",
                                  language_or_category=language, limit=limit)

    async def search_stories(self, query: str, story_metadata: Dict, category: Optional[str] = None, limit: int = 5) -> List[SearchResult]:
        """Search for stories using Qdrant or fallback to text search"""
        if self.is_qdrant_initialized:
            try:
                qdrant_results = await self.qdrant_search.search_stories(query, category, limit)
                # Convert to SearchResult format
                results = []
                for result in qdrant_results:
                    results.append(SearchResult(
                        title=result.title,
                        filename=result.filename,
                        language_or_category=result.language_or_category,
                        score=result.score,
                        metadata=result.metadata
                    ))
                return results
            except Exception as e:
                self.logger.warning(f"Qdrant search failed, using fallback: {e}")

        # Fallback to text search
        return self._search_content(query, story_metadata, content_type="stories",
                                  language_or_category=category, limit=limit)

    def _search_content(self, query: str, metadata: Dict, content_type: str,
                       language_or_category: Optional[str] = None, limit: int = 5) -> List[SearchResult]:
        """Generic content search method"""
        results = []
        query_lower = query.lower()

        # Determine which collections to search
        collections_to_search = [language_or_category] if language_or_category else metadata.keys()

        for collection in collections_to_search:
            if collection not in metadata:
                continue

            collection_data = metadata[collection]

            # Handle dictionary structure where keys are titles
            for title, item_data in collection_data.items():
                score = self._calculate_similarity(query_lower, title, item_data)

                if score > 0:  # Only include items with some match
                    results.append(SearchResult(
                        title=title,
                        filename=item_data.get('filename', f"{title}.mp3"),
                        language_or_category=collection,
                        score=score,
                        metadata=item_data
                    ))

        # Sort by score (descending) and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _calculate_similarity(self, query_lower: str, title: str, item_data: Dict) -> float:
        """Calculate similarity score between query and item"""
        score = 0.0

        # Check title match
        title_lower = title.lower()
        if query_lower == title_lower:
            score += 1.0  # Perfect match
        elif query_lower in title_lower:
            score += 0.8  # Partial title match
        elif any(word in title_lower for word in query_lower.split()):
            score += 0.6  # Word match in title

        # Check romanized version
        romanized = item_data.get('romanized', '').lower()
        if romanized:
            if query_lower == romanized:
                score += 0.9
            elif query_lower in romanized:
                score += 0.7
            elif any(word in romanized for word in query_lower.split()):
                score += 0.5

        # Check alternatives
        alternatives = item_data.get('alternatives', [])
        if alternatives:
            for alt in alternatives:
                alt_lower = alt.lower()
                if query_lower == alt_lower:
                    score += 0.8
                elif query_lower in alt_lower:
                    score += 0.6
                elif any(word in alt_lower for word in query_lower.split()):
                    score += 0.4

        return score

    def get_random_item(self, metadata: Dict, language_or_category: Optional[str] = None) -> Optional[SearchResult]:
        """Get a random item from metadata"""
        if not metadata:
            return None

        if language_or_category and language_or_category in metadata:
            collection_data = metadata[language_or_category]
        else:
            # Pick from all collections
            all_items = []
            for collection, collection_data in metadata.items():
                for title, item_data in collection_data.items():
                    all_items.append((title, item_data, collection))

            if not all_items:
                return None

            title, item_data, collection = random.choice(all_items)
            return SearchResult(
                title=title,
                filename=item_data.get('filename', f"{title}.mp3"),
                language_or_category=collection,
                score=1.0,
                metadata=item_data
            )

        # Pick from specific collection
        if collection_data:
            title = random.choice(list(collection_data.keys()))
            item_data = collection_data[title]
            return SearchResult(
                title=title,
                filename=item_data.get('filename', f"{title}.mp3"),
                language_or_category=language_or_category,
                score=1.0,
                metadata=item_data
            )

        return None