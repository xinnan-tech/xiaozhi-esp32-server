import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ModuleStats:
    total_time: float = 0.0
    call_count: int = 0
    max_time: float = 0.0
    min_time: float = float('inf')
    history: List[float] = field(default_factory=list)

class PerformanceMonitor:
    def __init__(self):
        self.stats: Dict[str, ModuleStats] = defaultdict(ModuleStats)
        self.current_session = {}
    
    def record(self, module: str, duration: float):
        stats = self.stats[module]
        stats.total_time += duration
        stats.call_count += 1
        stats.max_time = max(stats.max_time, duration)
        stats.min_time = min(stats.min_time, duration)
        stats.history.append(duration)
    
    def get_summary(self) -> Dict:
        return {
            module: {
                "avg": stats.total_time / stats.call_count if stats.call_count else 0,
                "max": stats.max_time,
                "min": stats.min_time,
                "total_calls": stats.call_count
            }
            for module, stats in self.stats.items()
        }

monitor = PerformanceMonitor()

def track_performance(module_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            monitor.record(module_name, duration)
            return result
        return wrapper
    return decorator 
