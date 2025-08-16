# VAD and ASR Filtering Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to improve Voice Activity Detection (VAD) accuracy and reduce false positive transcriptions in the Xiaozhi ESP32 server system. The implementation focuses on reducing noise-triggered VAD events and filtering common false transcripts while preserving legitimate user input.

## Current Issues

1. **VAD False Triggers**
   - Background noise triggering voice detection
   - Environmental sounds (fans, rustling) causing false positives
   - Too sensitive to non-speech audio

2. **ASR False Transcripts**
   - Common false outputs: "yeah", "so", "thank you", "um", "uh"
   - Short random words from noise
   - Affecting response quality and user experience

## Implementation Plan

### Phase 1: VAD Optimization (Immediate)

#### 1.1 Configuration Updates
**File**: `main/xiaozhi-server/data/.config.yaml`

```yaml
VAD:
  SileroVAD:
    type: silero
    threshold: 0.7  # Increased from 0.5
    threshold_low: 0.4  # For hysteresis
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 1500  # Increased from 1000ms
    frame_window_threshold: 5  # Increase from default 3
```

#### 1.2 Advanced VAD Configuration (Optional)
```yaml
VAD:
  SileroVAD:
    # ... existing config ...
    # Advanced noise handling
    noise_suppression:
      enabled: true
      pre_emphasis: 0.97  # High-pass filter coefficient
      energy_threshold: 0.01  # Minimum energy level
      spectral_subtraction: true  # Remove stationary noise
```

### Phase 2: ASR Filtering System

#### 2.1 Context-Aware Filtering Module
**New File**: `main/xiaozhi-server/core/utils/asr_filter.py`

```python
from typing import Dict, List, Tuple, Optional
import re
from config.logger import setup_logging

logger = setup_logging()

class ASRFilter:
    """
    Context-aware ASR filtering system to reduce false positives
    while preserving legitimate user input
    """
    
    def __init__(self, config: Dict):
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
        
        # Always filter list
        if any(pattern in cleaned_text for pattern in self.always_filter):
            return True, "Matches always-filter pattern"
            
        # Mode-specific filtering
        if self.mode == 'strict':
            return self._strict_filter(cleaned_text, word_count)
        else:  # smart mode
            return self._smart_filter(cleaned_text, word_count, original_text, context)
    
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
```

#### 2.2 Configuration Schema
**Update**: `main/xiaozhi-server/data/.config.yaml`

```yaml
ASR:
  # ... existing ASR config ...
  
  filtering:
    enabled: true
    mode: "smart"  # Options: "strict", "smart", "disabled"
    
    # Basic thresholds
    min_word_count: 2
    min_char_length: 3
    
    # Filter lists
    standalone_false_positives:
      - "yeah"
      - "so"
      - "thanks"
      - "thank you"
      - "okay"
      - "ok"
      - "um"
      - "uh"
      - "ah"
      - "hmm"
      - "oh"
      - "well"
      - "yes"
      - "no"
    
    always_filter:
      - "test test test"
      - "one two three"
      - "testing testing"
      - "hello hello hello"
    
    # Smart mode settings
    smart_mode:
      consider_context: true
      time_window_ms: 500  # Time after bot speaks to consider as noise
      repetition_threshold: 3  # Filter if same word repeated this many times
```

### Phase 3: Integration Points

#### 3.1 Update ASR Base Class
**File**: `main/xiaozhi-server/core/providers/asr/base.py`

```python
# Add import
from core.utils.asr_filter import ASRFilter

# In __init__ method
self.asr_filter = ASRFilter(config) if config else None

# In handle_voice_stop method
async def handle_voice_stop(self, conn, asr_audio_task):
    # ... existing code ...
    
    # After getting transcript
    if self.asr_filter and transcript:
        should_filter, reason = self.asr_filter.should_filter(
            transcript, 
            context={
                'time_since_bot_utterance': time.time() - conn.last_bot_utterance_time,
                'expecting_response': conn.expecting_user_response,
                'recent_filtered': conn.recent_filtered_texts[-5:]
            }
        )
        
        if should_filter:
            logger.info(f"Filtered transcript: '{transcript}' - Reason: {reason}")
            conn.recent_filtered_texts.append(transcript)
            return
    
    # Continue with normal processing
```

#### 3.2 Update Text Processing Utility
**File**: `main/xiaozhi-server/core/utils/util.py`

```python
def remove_punctuation_and_length(text, config=None, use_filter=True):
    """
    Enhanced text processing with optional ASR filtering
    """
    # ... existing punctuation removal code ...
    
    if use_filter and config:
        from core.utils.asr_filter import ASRFilter
        asr_filter = ASRFilter(config)
        should_filter, reason = asr_filter.should_filter(result)
        
        if should_filter:
            return 0, ""
    
    return len(result), result
```

### Phase 4: Monitoring and Metrics

#### 4.1 Logging Enhancement
**File**: `main/xiaozhi-server/core/utils/asr_metrics.py`

```python
import json
from datetime import datetime
from collections import defaultdict

class ASRMetrics:
    """Track ASR filtering effectiveness"""
    
    def __init__(self):
        self.metrics = {
            'total_transcripts': 0,
            'filtered_count': 0,
            'filter_reasons': defaultdict(int),
            'filtered_words': defaultdict(int),
            'false_positive_rate': 0.0
        }
        
    def record_transcript(self, text: str, filtered: bool, reason: str = None):
        self.metrics['total_transcripts'] += 1
        
        if filtered:
            self.metrics['filtered_count'] += 1
            if reason:
                self.metrics['filter_reasons'][reason] += 1
            self.metrics['filtered_words'][text.lower()] += 1
    
    def calculate_stats(self):
        total = self.metrics['total_transcripts']
        if total > 0:
            self.metrics['false_positive_rate'] = (
                self.metrics['filtered_count'] / total * 100
            )
    
    def export_report(self, filepath: str):
        self.calculate_stats()
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'top_filtered_words': dict(
                sorted(self.metrics['filtered_words'].items(), 
                       key=lambda x: x[1], reverse=True)[:10]
            )
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
```

### Phase 5: Testing Strategy

#### 5.1 Unit Tests
**File**: `main/xiaozhi-server/tests/test_asr_filter.py`

```python
import pytest
from core.utils.asr_filter import ASRFilter

class TestASRFilter:
    
    @pytest.fixture
    def smart_filter(self):
        config = {
            'ASR': {
                'filtering': {
                    'enabled': True,
                    'mode': 'smart',
                    'min_word_count': 2,
                    'min_char_length': 3
                }
            }
        }
        return ASRFilter(config)
    
    def test_filter_single_false_positive(self, smart_filter):
        should_filter, reason = smart_filter.should_filter("yeah")
        assert should_filter == True
        
    def test_keep_legitimate_phrase(self, smart_filter):
        should_filter, reason = smart_filter.should_filter("Yeah, play some music")
        assert should_filter == False
        
    def test_filter_repeated_words(self, smart_filter):
        should_filter, reason = smart_filter.should_filter("test test test")
        assert should_filter == True
```

#### 5.2 Integration Tests
1. Test with recorded audio samples containing noise
2. Test with legitimate user commands
3. Measure false positive reduction rate
4. Ensure no legitimate commands are filtered

### Phase 6: Rollout Plan

#### 6.1 Gradual Deployment
1. **Week 1**: Deploy VAD configuration changes only
   - Monitor for improvements in noise rejection
   - Collect baseline metrics

2. **Week 2**: Enable ASR filtering in "smart" mode
   - Monitor filtered transcripts
   - Adjust filter lists based on data

3. **Week 3**: Fine-tune thresholds
   - Analyze metrics reports
   - Optimize for specific environment

#### 6.2 Rollback Strategy
1. Keep original configuration backed up
2. Feature flags for enabling/disabling filtering
3. Quick disable via config without code changes

### Performance Considerations

1. **Processing Overhead**
   - Filtering adds < 1ms per transcript
   - Negligible impact on response time

2. **Memory Usage**
   - Context tracking uses < 1KB per connection
   - Metrics collection uses < 100KB total

3. **CPU Impact**
   - Regex operations are lightweight
   - No heavy computations required

### Future Enhancements

1. **Machine Learning Integration**
   - Train classifier on filtered vs. legitimate transcripts
   - Adaptive threshold adjustment

2. **Multi-language Support**
   - Extend filtering to other languages
   - Language-specific false positive lists

3. **Advanced Noise Profiling**
   - Learn environment-specific noise patterns
   - Automatic VAD threshold adjustment

### Conclusion

This implementation plan provides a comprehensive approach to reducing VAD false triggers and ASR false positives while maintaining system responsiveness to legitimate user input. The phased approach allows for gradual deployment and optimization based on real-world usage data.