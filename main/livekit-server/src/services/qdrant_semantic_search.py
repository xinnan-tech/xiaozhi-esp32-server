"""
Qdrant Semantic Search Implementation for Music and Stories
Enhanced semantic search using vector database
"""

import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

# Qdrant and ML dependencies
try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.models import PointStruct, Filter, FieldCondition, Match
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class QdrantSearchResult:
    """Enhanced search result with vector scoring"""
    title: str
    filename: str
    language_or_category: str
    score: float
    metadata: Dict
    alternatives: List[str]
    romanized: str

class QdrantSemanticSearch:
    """
    Advanced semantic search using Qdrant vector database
    """

    def __init__(self):
        self.is_available = QDRANT_AVAILABLE
        self.client: Optional[QdrantClient] = None
        self.model: Optional[SentenceTransformer] = None
        self.is_initialized = False

        # Qdrant configuration from reference implementation
        self.config = {
            "qdrant_url": "https://a2482b9f-2c29-476e-9ff0-741aaaaf632e.eu-west-1-0.aws.cloud.qdrant.io",
            "qdrant_api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zPBGAqVGy-edbbgfNOJsPWV496BsnQ4ELOFvsLNyjsk",
            "music_collection": "xiaozhi_music",
            "stories_collection": "xiaozhi_stories",
            "embedding_model": "all-MiniLM-L6-v2",
            "search_limit": 10,
            "min_score_threshold": 0.3
        }

        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant dependencies not available, semantic search will be limited")

    async def initialize(self) -> bool:
        """Initialize Qdrant client and embedding model"""
        if not self.is_available:
            logger.warning("Qdrant not available, using fallback search")
            return False

        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=self.config["qdrant_url"],
                api_key=self.config["qdrant_api_key"]
            )

            # Test connection
            collections = self.client.get_collections()
            logger.info("Connected to Qdrant successfully")

            # Initialize embedding model
            self.model = SentenceTransformer(self.config["embedding_model"])
            logger.info(f"Loaded embedding model: {self.config['embedding_model']}")

            # Ensure collections exist
            await self._ensure_collections_exist()

            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant semantic search: {e}")
            return False

    async def _ensure_collections_exist(self):
        """Check that required collections exist in Qdrant cloud"""
        try:
            # Check music collection exists
            try:
                music_info = self.client.get_collection(self.config["music_collection"])
                logger.info(f"Music collection '{self.config['music_collection']}' found with {music_info.points_count} points")
            except Exception:
                logger.warning(f"Music collection '{self.config['music_collection']}' not found in cloud")

            # Check stories collection exists
            try:
                stories_info = self.client.get_collection(self.config["stories_collection"])
                logger.info(f"Stories collection '{self.config['stories_collection']}' found with {stories_info.points_count} points")
            except Exception:
                logger.warning(f"Stories collection '{self.config['stories_collection']}' not found in cloud")

        except Exception as e:
            logger.error(f"Error checking collections: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.model or not text:
            return []
        return self.model.encode(text).tolist()

    async def index_music_metadata(self, music_metadata: Dict) -> bool:
        """Skip indexing - use existing cloud collections"""
        logger.info("Skipping music indexing - using existing cloud collections")
        return True

    async def index_stories_metadata(self, stories_metadata: Dict) -> bool:
        """Skip indexing - use existing cloud collections"""
        logger.info("Skipping stories indexing - using existing cloud collections")
        return True

    async def search_music(self, query: str, language_filter: Optional[str] = None, limit: int = 5) -> List[QdrantSearchResult]:
        """Search for music using Qdrant"""
        if not self.is_initialized:
            return []

        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                return []

            # Build filter
            filter_conditions = []
            if language_filter:
                filter_conditions.append(
                    FieldCondition(key="language", match=Match(value=language_filter))
                )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Search in Qdrant
            search_results = self.client.query_points(
                collection_name=self.config["music_collection"],
                query=query_embedding,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
                score_threshold=self.config["min_score_threshold"]
            )

            # Convert results
            results = []
            for hit in search_results.points:
                results.append(QdrantSearchResult(
                    title=hit.payload['title'],
                    filename=hit.payload['filename'],
                    language_or_category=hit.payload['language'],
                    score=hit.score,
                    metadata=hit.payload,
                    alternatives=hit.payload.get('alternatives', []),
                    romanized=hit.payload.get('romanized', '')
                ))

            logger.debug(f"Qdrant music search found {len(results)} results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"Qdrant music search failed: {e}")
            return []

    async def search_stories(self, query: str, category_filter: Optional[str] = None, limit: int = 5) -> List[QdrantSearchResult]:
        """Search for stories using Qdrant"""
        if not self.is_initialized:
            return []

        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                return []

            # Build filter
            filter_conditions = []
            if category_filter:
                filter_conditions.append(
                    FieldCondition(key="category", match=Match(value=category_filter))
                )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Search in Qdrant
            search_results = self.client.query_points(
                collection_name=self.config["stories_collection"],
                query=query_embedding,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
                score_threshold=self.config["min_score_threshold"]
            )

            # Convert results
            results = []
            for hit in search_results.points:
                results.append(QdrantSearchResult(
                    title=hit.payload['title'],
                    filename=hit.payload['filename'],
                    language_or_category=hit.payload['category'],
                    score=hit.score,
                    metadata=hit.payload,
                    alternatives=hit.payload.get('alternatives', []),
                    romanized=hit.payload.get('romanized', '')
                ))

            logger.debug(f"Qdrant stories search found {len(results)} results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"Qdrant stories search failed: {e}")
            return []