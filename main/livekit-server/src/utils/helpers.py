import asyncio
import logging
from livekit.agents import metrics

logger = logging.getLogger("helpers")

class UsageManager:
    """Utility class for managing usage metrics and logging"""

    def __init__(self):
        self.usage_collector = metrics.UsageCollector()

    async def log_usage(self):
        """Log usage summary"""
        summary = self.usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
        return {
            "type": "usage_summary",
            "summary": summary.llm_prompt_tokens
        }

    def get_collector(self):
        """Get the usage collector instance"""
        return self.usage_collector