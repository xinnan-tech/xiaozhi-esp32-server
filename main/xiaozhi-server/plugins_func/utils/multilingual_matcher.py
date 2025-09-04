"""
Multilingual content matching utility for music and stories
Based on the multilingual AI music app guide
"""

import os
import json
import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
import re

class MultilingualMatcher:
    """
    Handles multilingual content matching using metadata.json files
    Supports fuzzy matching, romanization, and alternative names
    """
    
    def __init__(self, content_dir: str, content_ext: List[str]):
        self.content_dir = Path(content_dir)
        self.content_ext = content_ext
        self.metadata_cache = {}
        self.language_folders = []
        self._load_all_metadata()
    
    def _load_all_metadata(self):
        """Load metadata.json from all language folders"""
        if not self.content_dir.exists():
            return
        
        for folder in self.content_dir.iterdir():
            if folder.is_dir():
                metadata_file = folder / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            # Use lowercase key for lookups but preserve original folder path
                            self.metadata_cache[folder.name.lower()] = {
                                'metadata': metadata,
                                'folder_path': folder,
                                'original_name': folder.name  # Preserve original case
                            }
                            self.language_folders.append(folder.name.lower())
                    except Exception as e:
                        print(f"Error loading metadata from {metadata_file}: {e}")
    
    def detect_language_from_request(self, request: str) -> Optional[str]:
        """
        Detect language from user request
        Returns the language folder name if detected
        """
        request_lower = request.lower()
        
        # Language detection patterns (more comprehensive)
        language_patterns = {
            'english': [
                'english', 'english song', 'english music', 'in english',
                'any english', 'some english', 'play english'
            ],
            'hindi': [
                'hindi', 'hindi song', 'hindi music', 'in hindi', 'हिंदी',
                'any hindi', 'some hindi', 'play hindi'
            ],
            'telugu': [
                'telugu', 'telugu song', 'telugu music', 'in telugu', 'తెలుగు',
                'any telugu', 'some telugu', 'play telugu'
            ],
            'kannada': [
                'kannada', 'kannada song', 'kannada music', 'in kannada', 'ಕನ್ನಡ',
                'any kannada', 'some kannada', 'play kannada'
            ],
            'tamil': [
                'tamil', 'tamil song', 'tamil music', 'in tamil', 'தமிழ்',
                'any tamil', 'some tamil', 'play tamil'
            ],
            'phonics': [
                'phonics', 'phonics song', 'phonics music', 'alphabet', 'abc',
                'play phonics', 'learn phonics', 'phonics sounds'
            ]
        }
        
        # Check for exact pattern matches first
        for language, patterns in language_patterns.items():
            for pattern in patterns:
                if pattern in request_lower:
                    # Check if this language folder exists
                    if language in self.language_folders:
                        return language
        
        # Check for word boundary matches (more precise)
        for language, patterns in language_patterns.items():
            for pattern in patterns:
                if re.search(r'\b' + re.escape(pattern) + r'\b', request_lower):
                    if language in self.language_folders:
                        return language
        
        return None
    
    
    def extract_content_name_from_request(self, request: str) -> Optional[str]:
        """
        Extract content name from user request
        Removes common trigger words and language indicators
        """
        # First, check if this is a language-only request
        language_only_patterns = [
            r'\b(play|sing|put on|listen to)\s+(any\s+)?(english|hindi|telugu|kannada|tamil|phonics)\s+(song|music)\b',
            r'\b(english|hindi|telugu|kannada|tamil|phonics)\s+(song|music)\s+(please)?\b',
            r'\bplay\s+(some\s+)?(english|hindi|telugu|kannada|tamil|phonics)\b'
        ]
        
        request_lower = request.lower()
        for pattern in language_only_patterns:
            if re.search(pattern, request_lower):
                return None  # This is a language-only request, no specific content name
        
        # Remove trigger words more carefully
        trigger_patterns = [
            r'\b(play|sing|put on|listen to|hear|tell)\s+',  # Action words at start
            r'\s+(for me|please|now)\b',  # Politeness words at end
            r'\b(a|the|some)\s+(song|story|music)\b',  # Articles with content type
            r'\s+(song|story|music)\b',  # Content type words
            r'\bin\s+(english|hindi|telugu|kannada|tamil)\b'  # Language indicators
        ]
        
        cleaned = request.lower()
        for pattern in trigger_patterns:
            cleaned = re.sub(pattern, ' ', cleaned)
        
        # Remove extra spaces and punctuation
        cleaned = re.sub(r'[^\w\s]', '', cleaned).strip()
        cleaned = ' '.join(cleaned.split())  # Remove multiple spaces
        
        # Don't return very short or empty strings
        if len(cleaned) < 3:
            return None
            
        return cleaned if cleaned else None
    
    def is_language_only_request(self, request: str) -> bool:
        """
        Check if this is a language-only request (no specific content name)
        """
        request_lower = request.lower()
        
        # Patterns that indicate language-only requests
        language_only_patterns = [
            r'\b(play|sing|put on)\s+(any\s+)?(english|hindi|telugu|kannada|tamil|phonics)\s+(song|music)\b',
            r'\b(english|hindi|telugu|kannada|tamil|phonics)\s+(song|music)\b',
            r'\bplay\s+(some\s+)?(english|hindi|telugu|kannada|tamil|phonics)\b',
            r'\b(any|some)\s+(english|hindi|telugu|kannada|tamil|phonics)\b'
        ]
        
        for pattern in language_only_patterns:
            if re.search(pattern, request_lower):
                return True
        
        return False

    def find_content_match(self, request: str, language_hint: Optional[str] = None) -> Optional[Tuple[str, str, Dict]]:
        """
        Find the best matching content based on request
        Returns: (relative_file_path, language, metadata_entry) or None
        
        Args:
            request: User's request text
            language_hint: Optional language hint from request analysis
        """
        # Check if this is a language-only request
        if self.is_language_only_request(request):
            return None  # Let the caller handle language-specific random selection
        
        # Extract content name from request
        content_name = self.extract_content_name_from_request(request)
        if not content_name:
            return None
        
        # Detect language from request if not provided
        if not language_hint:
            language_hint = self.detect_language_from_request(request)
        
        best_match = None
        best_score = 0
        
        # Search order: specific language first, then all languages
        search_languages = []
        if language_hint and language_hint in self.language_folders:
            search_languages.append(language_hint)
        
        # Add all other languages
        for lang in self.language_folders:
            if lang not in search_languages:
                search_languages.append(lang)
        
        for language in search_languages:
            if language not in self.metadata_cache:
                continue
            
            metadata = self.metadata_cache[language]['metadata']
            folder_path = self.metadata_cache[language]['folder_path']
            
            for original_title, entry in metadata.items():
                # Calculate match scores
                scores = []
                
                # Score against original title
                scores.append(fuzz.ratio(content_name, original_title.lower()))
                
                # Score against romanized version
                if 'romanized' in entry:
                    scores.append(fuzz.ratio(content_name, entry['romanized'].lower()))
                
                # Score against alternatives
                if 'alternatives' in entry and entry['alternatives']:
                    for alt in entry['alternatives']:
                        scores.append(fuzz.ratio(content_name, alt.lower()))
                
                # Score against filename (without extension)
                if 'filename' in entry:
                    filename_base = os.path.splitext(entry['filename'])[0].lower()
                    scores.append(fuzz.ratio(content_name, filename_base))
                
                # Take the best score for this entry
                max_score = max(scores) if scores else 0
                
                # Boost score if language matches hint
                if language_hint and language == language_hint:
                    max_score += 10
                
                # Update best match if this is better
                if max_score > best_score and max_score > 60:  # Minimum threshold
                    best_score = max_score
                    file_path = folder_path / entry['filename']
                    relative_path = str(file_path.relative_to(self.content_dir))
                    # Ensure forward slashes for cross-platform compatibility
                    relative_path = relative_path.replace('\\', '/')
                    best_match = (relative_path, language, entry)
        
        return best_match
    
    def get_language_specific_content(self, language: str) -> List[Tuple[str, Dict]]:
        """
        Get all content from a specific language folder
        Returns: List of (relative_file_path, metadata_entry)
        """
        if language.lower() not in self.metadata_cache:
            return []
        
        language_data = self.metadata_cache[language.lower()]
        metadata = language_data['metadata']
        folder_path = language_data['folder_path']
        
        content_list = []
        for original_title, entry in metadata.items():
            if 'filename' in entry:
                file_path = folder_path / entry['filename']
                relative_path = str(file_path.relative_to(self.content_dir))
                # Ensure forward slashes for cross-platform compatibility
                relative_path = relative_path.replace('\\', '/')
                content_list.append((relative_path, entry))
        
        return content_list
    
    def get_all_content_with_metadata(self) -> List[Tuple[str, str, Dict]]:
        """
        Get all content from all languages with metadata
        Returns: List of (relative_file_path, language, metadata_entry)
        """
        all_content = []
        
        for language in self.language_folders:
            content_list = self.get_language_specific_content(language)
            for relative_path, entry in content_list:
                all_content.append((relative_path, language, entry))
        
        return all_content
    
    def fallback_to_filesystem(self) -> List[str]:
        """
        Fallback method to get content files directly from filesystem
        Used when metadata.json is not available
        """
        content_files = []
        
        if not self.content_dir.exists():
            return content_files
        
        for file_path in self.content_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.content_ext:
                relative_path = str(file_path.relative_to(self.content_dir))
                # Ensure forward slashes for cross-platform compatibility
                relative_path = relative_path.replace('\\', '/')
                content_files.append(relative_path)
        
        return content_files
    
    def get_content_info(self, relative_path: str) -> Dict:
        """
        Get metadata information for a specific content file
        """
        file_path = Path(relative_path)
        
        # Try to find in metadata
        for language in self.language_folders:
            if language not in self.metadata_cache:
                continue
            
            metadata = self.metadata_cache[language]['metadata']
            for original_title, entry in metadata.items():
                if entry.get('filename') == file_path.name:
                    return {
                        'title': original_title,
                        'language': language,
                        'romanized': entry.get('romanized', original_title),
                        'alternatives': entry.get('alternatives', []),
                        **entry
                    }
        
        # Fallback to filename-based info
        return {
            'title': file_path.stem,
            'language': file_path.parent.name if file_path.parent.name != '.' else 'unknown',
            'romanized': file_path.stem,
            'alternatives': []
        }