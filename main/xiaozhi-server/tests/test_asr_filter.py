import pytest
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.asr_filter import ASRFilter
from core.utils.asr_metrics import get_metrics, reset_metrics

class TestASRFilter:
    
    @pytest.fixture(autouse=True)
    def reset_global_metrics(self):
        """Reset global metrics before each test"""
        reset_metrics()
    
    @pytest.fixture
    def smart_filter_config(self):
        """Config for smart mode filter"""
        return {
            'filtering': {
                'enabled': True,
                'mode': 'smart',
                'min_word_count': 2,
                'min_char_length': 3,
                'standalone_false_positives': [
                    "yeah", "so", "thanks", "okay", "um", "uh", "ah", "hmm", "oh"
                ],
                'always_filter': [
                    "test test test", "one two three"
                ]
            }
        }
    
    @pytest.fixture
    def strict_filter_config(self):
        """Config for strict mode filter"""
        return {
            'filtering': {
                'enabled': True,
                'mode': 'strict',
                'min_word_count': 2,
                'min_char_length': 3,
                'standalone_false_positives': [
                    "yeah", "so", "thanks", "okay", "um", "uh", "ah", "hmm", "oh"
                ]
            }
        }
    
    @pytest.fixture
    def disabled_filter_config(self):
        """Config for disabled filter"""
        return {
            'filtering': {
                'enabled': False
            }
        }
    
    def test_filter_single_false_positive_smart_mode(self, smart_filter_config):
        """Test filtering single false positive words in smart mode"""
        filter = ASRFilter(smart_filter_config)
        
        # Should filter single false positives without context
        should_filter, reason = filter.should_filter("yeah")
        assert should_filter == True
        assert "noise" in reason.lower()
        
        should_filter, reason = filter.should_filter("um")
        assert should_filter == True
        
    def test_keep_legitimate_phrase_smart_mode(self, smart_filter_config):
        """Test keeping legitimate phrases in smart mode"""
        filter = ASRFilter(smart_filter_config)
        
        # Should keep longer phrases
        should_filter, reason = filter.should_filter("Yeah, play some music")
        assert should_filter == False
        
        should_filter, reason = filter.should_filter("Thanks for helping me")
        assert should_filter == False
        
    def test_filter_always_filter_patterns(self, smart_filter_config):
        """Test filtering always-filter patterns"""
        filter = ASRFilter(smart_filter_config)
        
        should_filter, reason = filter.should_filter("test test test")
        assert should_filter == True
        assert "always-filter" in reason
        
        should_filter, reason = filter.should_filter("one two three")
        assert should_filter == True
        
    def test_filter_repeated_words(self, smart_filter_config):
        """Test filtering repeated word patterns"""
        filter = ASRFilter(smart_filter_config)
        
        should_filter, reason = filter.should_filter("hello hello hello")
        assert should_filter == True
        assert "repeated" in reason.lower()
        
        should_filter, reason = filter.should_filter("no no no no")
        assert should_filter == True
        
    def test_context_aware_filtering(self, smart_filter_config):
        """Test context-aware filtering for responses"""
        filter = ASRFilter(smart_filter_config)
        
        # Should keep yes/no responses when expecting response
        context = {'expecting_response': True}
        should_filter, reason = filter.should_filter("yes", context)
        assert should_filter == False
        assert "response to question" in reason.lower()
        
        should_filter, reason = filter.should_filter("yeah", context)
        assert should_filter == False
        
    def test_strict_mode_filtering(self, strict_filter_config):
        """Test strict mode filtering"""
        filter = ASRFilter(strict_filter_config)
        
        # Should filter short text
        should_filter, reason = filter.should_filter("hi")
        assert should_filter == True
        assert "chars" in reason
        
        # Should filter single words
        should_filter, reason = filter.should_filter("hello")
        assert should_filter == True
        assert "words" in reason
        
        # Should keep longer phrases
        should_filter, reason = filter.should_filter("hello world")
        assert should_filter == False
        
    def test_disabled_filter(self, disabled_filter_config):
        """Test disabled filter mode"""
        filter = ASRFilter(disabled_filter_config)
        
        # Should not filter anything
        should_filter, reason = filter.should_filter("yeah")
        assert should_filter == False
        assert "disabled" in reason.lower()
        
        should_filter, reason = filter.should_filter("test test test")
        assert should_filter == False
        
    def test_timing_based_filtering(self, smart_filter_config):
        """Test filtering based on timing after bot utterance"""
        filter = ASRFilter(smart_filter_config)
        
        # Should filter single words that come immediately after bot speaks
        context = {
            'time_since_bot_utterance': 0.3,  # 300ms after bot
            'expecting_response': False
        }
        should_filter, reason = filter.should_filter("yeah", context)
        assert should_filter == True
        
        # Should not filter if enough time has passed
        context['time_since_bot_utterance'] = 2.0  # 2 seconds after bot
        should_filter, reason = filter.should_filter("yeah", context)
        assert should_filter == True  # Still filtered as single word without context
        
    def test_recent_filtered_pattern(self, smart_filter_config):
        """Test filtering based on recent filtered patterns"""
        filter = ASRFilter(smart_filter_config)
        
        # Should filter if word was recently filtered
        context = {
            'recent_filtered': ['yeah', 'um', 'ah']
        }
        should_filter, reason = filter.should_filter("yeah", context)
        assert should_filter == True
        
    def test_question_detection(self, smart_filter_config):
        """Test question detection for bot utterances"""
        filter = ASRFilter(smart_filter_config)
        
        filter.update_context('bot_utterance', "Do you want to play music?")
        assert filter.expecting_response == True
        
        filter.update_context('bot_utterance', "What is your name?")
        assert filter.expecting_response == True
        
        filter.update_context('bot_utterance', "I'm playing music for you.")
        assert filter.expecting_response == False
        
    def test_metrics_tracking(self, smart_filter_config):
        """Test that metrics are properly tracked"""
        filter = ASRFilter(smart_filter_config)
        metrics = get_metrics()
        
        # Filter some transcripts
        filter.should_filter("yeah")
        filter.should_filter("Play some music please")
        filter.should_filter("test test test")
        
        # Check metrics
        summary = metrics.get_summary()
        assert summary['total_transcripts'] == 3
        assert summary['filtered_count'] == 2
        assert summary['false_positive_rate'] > 0
        
    def test_edge_cases(self, smart_filter_config):
        """Test edge cases"""
        filter = ASRFilter(smart_filter_config)
        
        # Empty string
        should_filter, reason = filter.should_filter("")
        assert should_filter == True
        
        # Very short text
        should_filter, reason = filter.should_filter("a")
        assert should_filter == True
        
        # Punctuation only
        should_filter, reason = filter.should_filter("...")
        assert should_filter == True
        
        # Mixed case
        should_filter, reason = filter.should_filter("YeAh")
        assert should_filter == True
        
        # With punctuation
        should_filter, reason = filter.should_filter("yeah!")
        assert should_filter == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])