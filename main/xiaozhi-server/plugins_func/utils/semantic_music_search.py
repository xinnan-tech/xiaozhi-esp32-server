"""
Semantic Music Search Module using Qdrant Vector Database
Integrates with the existing multilingual music matching system
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.http.exceptions import UnexpectedResponse
    from sentence_transformers import SentenceTransformer
    from spellchecker import SpellChecker
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    import_error = str(e)

import hashlib
import time

@dataclass
class MusicSearchResult:
    """Data class for music search results"""
    file_path: str
    title: str
    language: str
    romanized: str
    alternatives: List[str]
    score: float
    metadata: Dict

class SemanticMusicSearch:
    """
    Semantic music search engine using Qdrant vector database
    """
    
    def __init__(self, config: Dict = None):
        """Initialize the semantic music search system"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Check if dependencies are available
        if not DEPENDENCIES_AVAILABLE:
            self.logger.error(f"Semantic search dependencies not available: {import_error}")
            self.is_available = False
            return
        
        self.is_available = True
        
        # Qdrant configuration

        self.qdrant_url = self.config.get("qdrant_url", "https://a2482b9f-2c29-476e-9ff0-741aaaaf632e.eu-west-1-0.aws.cloud.qdrant.io")
        self.qdrant_api_key = self.config.get("qdrant_api_key", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zPBGAqVGy-edbbgfNOJsPWV496BsnQ4ELOFvsLNyjsk")

        self.collection_name = self.config.get("collection_name", "xiaozhi_music")
        
        # Embedding model configuration
        self.model_name = self.config.get("embedding_model", "all-MiniLM-L6-v2")
        
        # Search parameters
        self.search_limit = self.config.get("search_limit", 5)
        self.min_score_threshold = self.config.get("min_score_threshold", 0.5)
        
        # Initialize components
        self.qdrant_client = None
        self.embedding_model = None
        self.spell_checker = None
        self.embedding_size = None
        self.is_initialized = False
        
        # Cache for embeddings to avoid recomputation
        self.embedding_cache = {}
        
    def initialize(self) -> bool:
        """Initialize Qdrant client and embedding model"""
        if not self.is_available:
            self.logger.error("Semantic search dependencies not available")
            return False
            
        try:
            # Initialize spell checker
            self.spell_checker = SpellChecker()
            
            # Initialize Qdrant client
            if self.qdrant_api_key:
                self.qdrant_client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key
                )
            else:
                self.qdrant_client = QdrantClient(url=self.qdrant_url)
            
            # Test connection
            self.qdrant_client.get_collections()
            
            # Initialize embedding model
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)
            self.embedding_size = self.embedding_model.get_sentence_embedding_dimension()
            
            # Create collection if it doesn't exist
            self._create_collection_if_not_exists()
            
            self.is_initialized = True
            self.logger.info(f"Semantic music search initialized with model: {self.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize semantic search: {e}")
            self.is_initialized = False
            return False
    
    def _create_collection_if_not_exists(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            self.qdrant_client.get_collection(collection_name=self.collection_name)
            self.logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception:
            self.logger.info(f"Creating collection '{self.collection_name}'")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=models.Distance.COSINE
                ),
            )
    
    def correct_spelling(self, query: str) -> str:
        """Correct spelling in the user query"""
        if not self.spell_checker:
            return query
            
        words = query.split()
        corrected_words = []
        
        for word in words:
            # Skip very short words and numbers
            if len(word) <= 2 or word.isdigit():
                corrected_words.append(word)
                continue
                
            corrected_word = self.spell_checker.correction(word)
            if corrected_word is None:
                corrected_word = word
            corrected_words.append(corrected_word)
        
        corrected_query = " ".join(corrected_words)
        if corrected_query != query:
            self.logger.debug(f"Spelling correction: '{query}' -> '{corrected_query}'")
        
        return corrected_query
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with caching"""
        if not text or not self.embedding_model:
            return []
            
        # Create a hash of the text for caching
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        embedding = self.embedding_model.encode(text).tolist()
        self.embedding_cache[text_hash] = embedding
        return embedding
    
    def index_music_metadata(self, music_metadata: Dict[str, Dict]) -> bool:
        """
        Index music metadata into Qdrant
        music_metadata format: {language: {metadata: {song_title: song_info}}}
        """
        if not self.is_initialized:
            self.logger.warning("Semantic search not initialized, skipping indexing")
            return False
        
        try:
            # Clear existing collection
            self.qdrant_client.delete_collection(self.collection_name)
            self._create_collection_if_not_exists()
            
            points = []
            point_id = 0
            
            for language, lang_data in music_metadata.items():
                metadata = lang_data.get('metadata', {})
                
                for song_title, song_info in metadata.items():
                    # Prepare searchable text for embedding
                    searchable_texts = [
                        song_title,  # Original title
                        song_info.get('romanized', ''),  # Romanized version
                    ]
                    
                    # Add alternative names
                    alternatives = song_info.get('alternatives', [])
                    if isinstance(alternatives, list):
                        searchable_texts.extend(alternatives)
                    
                    # Add keywords
                    keywords = song_info.get('keywords', [])
                    if isinstance(keywords, list):
                        searchable_texts.extend(keywords)
                    
                    # Add language for context
                    searchable_texts.append(language)
                    
                    # Combine all searchable text
                    combined_text = " ".join(filter(None, searchable_texts)).strip()
                    
                    if not combined_text:
                        continue
                    
                    # Generate embedding
                    embedding = self._get_embedding(combined_text)
                    if not embedding:
                        continue
                    
                    # Prepare payload
                    payload = {
                        'title': song_title,
                        'language': language,
                        'romanized': song_info.get('romanized', song_title),
                        'alternatives': alternatives,
                        'keywords': keywords,
                        'filename': song_info.get('filename', f"{song_title}.mp3"),
                        'file_path': f"{language}/{song_info.get('filename', f'{song_title}.mp3')}",
                        'searchable_text': combined_text,
                        'metadata': song_info
                    }
                    
                    points.append(
                        models.PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=payload
                        )
                    )
                    point_id += 1
            
            # Upsert points to Qdrant
            if points:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                self.logger.info(f"Indexed {len(points)} music tracks into Qdrant")
                return True
            else:
                self.logger.warning("No music metadata to index")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to index music metadata: {e}")
            return False
    
    def search(self, query: str, limit: Optional[int] = None) -> List[MusicSearchResult]:
        """
        Perform semantic search for music
        """
        if not self.is_initialized:
            return []
        
        try:
            # Check if collection has data
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            if collection_info.points_count == 0:
                self.logger.warning("Music collection is empty. Please index music metadata first.")
                return []
            
            # Correct spelling
            corrected_query = self.correct_spelling(query)
            
            # Generate query embedding
            query_embedding = self._get_embedding(corrected_query)
            if not query_embedding:
                return []
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit or self.search_limit
            )
            
            # Convert to MusicSearchResult objects
            results = []
            for hit in search_results:
                if hit.score >= self.min_score_threshold:
                    result = MusicSearchResult(
                        file_path=hit.payload['file_path'],
                        title=hit.payload['title'],
                        language=hit.payload['language'],
                        romanized=hit.payload['romanized'],
                        alternatives=hit.payload['alternatives'],
                        score=hit.score,
                        metadata=hit.payload['metadata']
                    )
                    results.append(result)
            
            self.logger.debug(f"Found {len(results)} matching songs for query: '{query}'")
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def find_best_match(self, query: str) -> Optional[MusicSearchResult]:
        """Find the single best matching song"""
        results = self.search(query, limit=1)
        return results[0] if results else None
    
    def is_collection_indexed(self) -> bool:
        """Check if the collection has been indexed"""
        if not self.is_initialized:
            return False
        
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return collection_info.points_count > 0
        except:
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the indexed collection"""
        if not self.is_initialized:
            return {}
        
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                'points_count': collection_info.points_count,
                'segments_count': collection_info.segments_count,
            }
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {}