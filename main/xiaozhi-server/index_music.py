#!/usr/bin/env python3
"""
Music Metadata Indexing Script for Semantic Search
Run this script to index all music metadata into Qdrant vector database
Usage: python index_music.py [--clear] [--verify]
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import hashlib
from ruamel.yaml import YAML

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class IndexingStats:
    """Statistics for indexing operation"""
    total_languages: int = 0
    total_songs: int = 0
    songs_indexed: int = 0
    songs_failed: int = 0
    time_taken: float = 0
    languages_processed: List[str] = None
    
    def __post_init__(self):
        if self.languages_processed is None:
            self.languages_processed = []

class MusicIndexer:
    """Handles indexing of music metadata into Qdrant"""
    
    def __init__(self, config_path: str = "data/.config.yaml"):
        """Initialize the indexer with configuration"""
        self.config = self._load_config(config_path)
        self.stats = IndexingStats()
        
        # Get semantic search config
        self.semantic_config = self.config.get('semantic_search', {})
        if not self.semantic_config.get('enabled', False):
            logger.warning("Semantic search is disabled in configuration!")
        
        # Qdrant settings
        self.qdrant_url = self.semantic_config.get('qdrant_url')
        self.qdrant_api_key = self.semantic_config.get('qdrant_api_key')
        self.collection_name = self.semantic_config.get('collection_name', 'xiaozhi_music')
        
        # Embedding settings
        self.model_name = self.semantic_config.get('embedding_model', 'all-MiniLM-L6-v2')
        
        # Music directory settings
        self.music_dir = Path(self.config.get('plugins', {}).get('play_music', {}).get('music_dir', './music'))
        self.music_ext = ('.mp3', '.wav', '.p3')
        
        # Initialize clients
        self.qdrant_client = None
        self.embedding_model = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        yaml = YAML()
        yaml.preserve_quotes = True
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    
    def initialize(self) -> bool:
        """Initialize Qdrant client and embedding model"""
        try:
            # Initialize Qdrant client
            logger.info(f"Connecting to Qdrant at {self.qdrant_url}...")
            self.qdrant_client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                timeout=60  # Increased timeout
            )
            
            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Connected to Qdrant. Found {len(collections.collections)} collections")
            
            # Initialize embedding model
            logger.info(f"Loading embedding model: {self.model_name}...")
            self.embedding_model = SentenceTransformer(self.model_name)
            self.embedding_size = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded. Dimension: {self.embedding_size}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def create_collection(self, recreate: bool = False) -> bool:
        """Create or recreate the Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if exists:
                if recreate:
                    logger.info(f"Deleting existing collection '{self.collection_name}'...")
                    self.qdrant_client.delete_collection(self.collection_name)
                    logger.info("Collection deleted")
                else:
                    logger.info(f"Collection '{self.collection_name}' already exists")
                    return True
            
            # Create new collection
            logger.info(f"Creating collection '{self.collection_name}'...")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=models.Distance.COSINE
                ),
            )
            logger.info("Collection created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False
    
    def load_music_metadata(self) -> Dict[str, Dict]:
        """Load all music metadata from the music directory"""
        metadata_cache = {}
        
        if not self.music_dir.exists():
            logger.error(f"Music directory does not exist: {self.music_dir}")
            return metadata_cache
        
        logger.info(f"Scanning music directory: {self.music_dir}")
        
        for language_folder in self.music_dir.iterdir():
            if not language_folder.is_dir():
                continue
            
            language_name = language_folder.name
            metadata_file = language_folder / "metadata.json"
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    metadata_cache[language_name] = {
                        'metadata': metadata,
                        'folder_path': str(language_folder)
                    }
                    
                    self.stats.total_songs += len(metadata)
                    self.stats.languages_processed.append(language_name)
                    logger.info(f"Loaded {len(metadata)} songs from {language_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load metadata from {metadata_file}: {e}")
            else:
                # Scan for actual music files if no metadata.json
                music_files = []
                for ext in self.music_ext:
                    music_files.extend(language_folder.glob(f"*{ext}"))
                
                if music_files:
                    logger.warning(f"No metadata.json in {language_name}, found {len(music_files)} music files")
                    # Create basic metadata from filenames
                    metadata = {}
                    for file in music_files:
                        song_name = file.stem
                        metadata[song_name] = {
                            'filename': file.name,
                            'romanized': song_name
                        }
                    
                    metadata_cache[language_name] = {
                        'metadata': metadata,
                        'folder_path': str(language_folder)
                    }
                    
                    self.stats.total_songs += len(metadata)
                    self.stats.languages_processed.append(language_name)
        
        self.stats.total_languages = len(metadata_cache)
        logger.info(f"Total: {self.stats.total_languages} languages, {self.stats.total_songs} songs")
        return metadata_cache
    
    def index_metadata(self, metadata_cache: Dict[str, Dict]) -> bool:
        """Index all metadata into Qdrant"""
        if not metadata_cache:
            logger.warning("No metadata to index")
            return False
        
        try:
            points = []
            point_id = 0
            
            logger.info("Generating embeddings and preparing data...")
            
            for language, lang_data in metadata_cache.items():
                metadata = lang_data.get('metadata', {})
                
                for song_title, song_info in metadata.items():
                    try:
                        # Prepare searchable text
                        searchable_texts = [
                            song_title,
                            song_info.get('romanized', ''),
                        ]
                        
                        # Add alternatives
                        alternatives = song_info.get('alternatives', [])
                        if isinstance(alternatives, list):
                            searchable_texts.extend(alternatives)
                        
                        # Add keywords
                        keywords = song_info.get('keywords', [])
                        if isinstance(keywords, list):
                            searchable_texts.extend(keywords)
                        
                        # Add language context
                        searchable_texts.append(language)
                        
                        # Combine all text
                        combined_text = " ".join(filter(None, searchable_texts)).strip()
                        
                        if not combined_text:
                            logger.warning(f"Skipping {song_title} - no searchable text")
                            continue
                        
                        # Generate embedding
                        embedding = self.embedding_model.encode(combined_text).tolist()
                        
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
                        self.stats.songs_indexed += 1
                        
                        if point_id % 50 == 0:
                            logger.info(f"Processed {point_id} songs...")
                        
                    except Exception as e:
                        logger.error(f"Failed to process {song_title}: {e}")
                        self.stats.songs_failed += 1
            
            # Upload to Qdrant in batches
            if points:
                logger.info(f"Uploading {len(points)} songs to Qdrant...")
                batch_size = 100
                
                for i in range(0, len(points), batch_size):
                    batch = points[i:i+batch_size]
                    self.qdrant_client.upsert(
                        collection_name=self.collection_name,
                        points=batch,
                        wait=True  # Wait for indexing to complete
                    )
                    logger.info(f"Uploaded batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")
                
                logger.info(f"Successfully indexed {len(points)} songs")
                return True
            else:
                logger.warning("No valid songs to index")
                return False
                
        except Exception as e:
            logger.error(f"Failed to index metadata: {e}")
            return False
    
    def verify_indexing(self) -> bool:
        """Verify that indexing was successful"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            point_count = collection_info.points_count
            
            logger.info(f"Collection '{self.collection_name}' contains {point_count} songs")
            
            # Try a sample search
            test_query = "twinkle twinkle little star"
            logger.info(f"Testing search with query: '{test_query}'")
            
            query_embedding = self.embedding_model.encode(test_query).tolist()
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=3
            )
            
            if results:
                logger.info("Sample search results:")
                for i, hit in enumerate(results, 1):
                    logger.info(f"  {i}. {hit.payload['title']} ({hit.payload['language']}) - Score: {hit.score:.3f}")
            else:
                logger.warning("No results found for test query")
            
            return point_count > 0
            
        except Exception as e:
            logger.error(f"Failed to verify indexing: {e}")
            return False
    
    def run(self, clear: bool = False, verify_only: bool = False):
        """Run the indexing process"""
        start_time = time.time()
        
        # Initialize
        if not self.initialize():
            logger.error("Initialization failed")
            return False
        
        if verify_only:
            # Just verify existing index
            success = self.verify_indexing()
            if success:
                logger.info("✅ Verification successful")
            else:
                logger.error("❌ Verification failed")
            return success
        
        # Create/recreate collection
        if not self.create_collection(recreate=clear):
            logger.error("Failed to create collection")
            return False
        
        # Load metadata
        metadata_cache = self.load_music_metadata()
        if not metadata_cache:
            logger.error("No metadata found")
            return False
        
        # Index metadata
        success = self.index_metadata(metadata_cache)
        
        # Calculate stats
        self.stats.time_taken = time.time() - start_time
        
        # Print summary
        logger.info("=" * 60)
        logger.info("INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Languages processed: {self.stats.total_languages}")
        logger.info(f"Total songs found: {self.stats.total_songs}")
        logger.info(f"Songs indexed: {self.stats.songs_indexed}")
        logger.info(f"Songs failed: {self.stats.songs_failed}")
        logger.info(f"Time taken: {self.stats.time_taken:.2f} seconds")
        logger.info(f"Languages: {', '.join(self.stats.languages_processed)}")
        logger.info("=" * 60)
        
        if success:
            logger.info("✅ Indexing completed successfully!")
            # Verify the indexing
            self.verify_indexing()
        else:
            logger.error("❌ Indexing failed")
        
        return success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Index music metadata for semantic search')
    parser.add_argument('--clear', action='store_true', help='Clear existing index before indexing')
    parser.add_argument('--verify', action='store_true', help='Only verify existing index')
    parser.add_argument('--config', default='data/.config.yaml', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 60)
    print("MUSIC METADATA INDEXER FOR XIAOZHI")
    print("=" * 60)
    print(f"Config file: {args.config}")
    print(f"Clear existing: {args.clear}")
    print(f"Verify only: {args.verify}")
    print("=" * 60)
    print()
    
    # Run indexer
    indexer = MusicIndexer(config_path=args.config)
    success = indexer.run(clear=args.clear, verify_only=args.verify)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()