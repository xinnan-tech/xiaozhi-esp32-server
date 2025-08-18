import json
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any
from config.logger import setup_logging

logger = setup_logging()

class ASRMetrics:
    """Track ASR filtering effectiveness"""
    
    def __init__(self):
        self.metrics = {
            'total_transcripts': 0,
            'filtered_count': 0,
            'filter_reasons': defaultdict(int),
            'filtered_words': defaultdict(int),
            'false_positive_rate': 0.0,
            'session_start': datetime.now().isoformat()
        }
        
    def record_transcript(self, text: str, filtered: bool, reason: str = None):
        """Record a transcript and whether it was filtered"""
        self.metrics['total_transcripts'] += 1
        
        if filtered:
            self.metrics['filtered_count'] += 1
            if reason:
                self.metrics['filter_reasons'][reason] += 1
            # Track filtered words/phrases
            self.metrics['filtered_words'][text.lower()] += 1
    
    def calculate_stats(self):
        """Calculate filtering statistics"""
        total = self.metrics['total_transcripts']
        if total > 0:
            self.metrics['false_positive_rate'] = (
                self.metrics['filtered_count'] / total * 100
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        self.calculate_stats()
        return {
            'total_transcripts': self.metrics['total_transcripts'],
            'filtered_count': self.metrics['filtered_count'],
            'false_positive_rate': round(self.metrics['false_positive_rate'], 2),
            'top_filter_reasons': dict(
                sorted(self.metrics['filter_reasons'].items(), 
                       key=lambda x: x[1], reverse=True)[:5]
            ),
            'top_filtered_words': dict(
                sorted(self.metrics['filtered_words'].items(), 
                       key=lambda x: x[1], reverse=True)[:10]
            )
        }
    
    def export_report(self, filepath: str = None):
        """Export metrics report to file"""
        self.calculate_stats()
        
        # Default filepath if not provided
        if not filepath:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "asr_metrics")
            os.makedirs(log_dir, exist_ok=True)
            filepath = os.path.join(log_dir, f"asr_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'session_start': self.metrics['session_start'],
            'metrics': {
                'total_transcripts': self.metrics['total_transcripts'],
                'filtered_count': self.metrics['filtered_count'],
                'false_positive_rate': round(self.metrics['false_positive_rate'], 2)
            },
            'filter_reasons': dict(self.metrics['filter_reasons']),
            'top_filtered_words': dict(
                sorted(self.metrics['filtered_words'].items(), 
                       key=lambda x: x[1], reverse=True)[:20]
            )
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        logger.info(f"ASR metrics report exported to {filepath}")
        return filepath
    
    def reset(self):
        """Reset all metrics"""
        self.__init__()


# Global metrics instance
_global_metrics = None

def get_metrics() -> ASRMetrics:
    """Get global ASR metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ASRMetrics()
    return _global_metrics

def reset_metrics():
    """Reset global metrics"""
    global _global_metrics
    if _global_metrics:
        _global_metrics.reset()