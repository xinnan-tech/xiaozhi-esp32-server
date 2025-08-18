from typing import Dict, List, Tuple, Optional
import re
from config.logger import setup_logging
from core.utils.asr_metrics import get_metrics

logger = setup_logging()

class ASRFilter:
    """
    Context-aware ASR filtering system to reduce false positives
    while preserving legitimate user input
    """
    
    def __init__(self, config: Dict):
        # Check if config has filtering directly (when passed from modules_initialize)
        if 'filtering' in config:
            self.config = config.get('filtering', {})
        else:
            # Fallback to ASR.filtering if available
            self.config = config.get('ASR', {}).get('filtering', {})
        
        self.enabled = self.config.get('enabled', True)
        self.mode = self.config.get('mode', 'smart')  # strict, smart, disabled
        self.min_word_count = self.config.get('min_word_count', 2)
        self.min_char_length = self.config.get('min_char_length', 3)
        
        # Load filter lists
        self.standalone_false_positives = self.config.get(
            'standalone_false_positives', 
            ["yeah", "so", "thanks", "okay", "um", "uh", "ah", "hmm", "oh"]
        )
        self.always_filter = self.config.get(
            'always_filter',
            ["test test test", "one two three"]
        )
        
        # Context tracking
        self.last_bot_utterance = ""
        self.expecting_response = False
        self.conversation_context = []
        
    def should_filter(self, text: str, context: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Determine if transcript should be filtered
        Returns: (should_filter, reason)
        """
        if not self.enabled or self.mode == 'disabled':
            return False, "Filtering disabled"
            
        # Clean and prepare text
        original_text = text.strip()
        cleaned_text = self._clean_text(text)
        word_count = len(original_text.split())
        
        # Determine if should filter
        should_filter = False
        reason = ""
        
        # Always filter list
        if any(pattern in cleaned_text for pattern in self.always_filter):
            should_filter = True
            reason = "Matches always-filter pattern"
        # Mode-specific filtering
        elif self.mode == 'strict':
            should_filter, reason = self._strict_filter(cleaned_text, word_count)
        else:  # smart mode
            should_filter, reason = self._smart_filter(cleaned_text, word_count, original_text, context)
        
        # Track metrics
        metrics = get_metrics()
        metrics.record_transcript(original_text, should_filter, reason)
        
        return should_filter, reason
    
    def _clean_text(self, text: str) -> str:
        """Remove punctuation and normalize text"""
        # Remove punctuation but keep spaces
        cleaned = re.sub(r'[^\w\s]', '', text)
        return cleaned.strip().lower()
    
    def _strict_filter(self, text: str, word_count: int) -> Tuple[bool, str]:
        """Strict filtering mode"""
        if len(text) < self.min_char_length:
            return True, f"Too short ({len(text)} chars)"
            
        if word_count < self.min_word_count:
            return True, f"Too few words ({word_count})"
            
        if text in self.standalone_false_positives:
            return True, "Matches false positive list"
            
        return False, "Passed strict filter"
    
    def _smart_filter(self, text: str, word_count: int, 
                     original: str, context: Optional[Dict]) -> Tuple[bool, str]:
        """Smart context-aware filtering"""
        
        # Very short text
        if len(text) < 2:
            return True, "Single character or empty"
        
        # Check if it's a response to a yes/no question
        if context and context.get('expecting_response'):
            if text in ['yes', 'no', 'yeah', 'nope', 'okay', 'sure']:
                return False, "Valid response to question"
        
        # Single word that's commonly a false positive
        if word_count == 1 and text in self.standalone_false_positives:
            # Check conversation context
            if self._is_likely_noise(text, context):
                return True, "Likely noise (single word, no context)"
        
        # Multiple identical words (often noise)
        words = text.split()
        if len(set(words)) == 1 and len(words) > 2:
            return True, "Repeated word pattern"
        
        # Part of a longer phrase - usually legitimate
        if word_count >= 3:
            return False, "Part of longer phrase"
            
        return False, "Passed smart filter"
    
    def _is_likely_noise(self, text: str, context: Optional[Dict]) -> bool:
        """Determine if single word is likely noise based on context"""
        if not context:
            return True
            
        # Check timing - if it comes immediately after bot stops speaking
        time_since_bot = context.get('time_since_bot_utterance', float('inf'))
        if time_since_bot < 0.5:  # Within 500ms
            return True
            
        # Check if it matches recent pattern of noise
        recent_filtered = context.get('recent_filtered', [])
        if text in recent_filtered:
            return True
            
        return False
    
    def update_context(self, key: str, value: any):
        """Update filtering context"""
        if key == 'bot_utterance':
            self.last_bot_utterance = value
            self.expecting_response = self._is_question(value)
        elif key == 'conversation':
            self.conversation_context.append(value)
            # Keep last 10 exchanges
            self.conversation_context = self.conversation_context[-10:]
    
    def _is_question(self, text: str) -> bool:
        """Check if bot utterance is a question"""
        question_patterns = [
            r'\?$',  # Ends with ?
            r'^(do|does|did|will|would|can|could|should|is|are|what|where|when|why|how)',
            r'(right|correct|okay|yes or no)[\?\.]?$'
        ]
        return any(re.search(pattern, text.lower()) for pattern in question_patterns)