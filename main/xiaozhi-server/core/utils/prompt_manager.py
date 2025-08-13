"""
System prompt manager module
Responsible for managing and updating system prompts, including quick initialization and async enhancement features
"""

import os
import cnlunar
from typing import Dict, Any
from config.logger import setup_logging
from jinja2 import Template

TAG = __name__

WEEKDAY_MAP = {
    "Monday": "Monday",
    "Tuesday": "Tuesday",
    "Wednesday": "Wednesday",
    "Thursday": "Thursday",
    "Friday": "Friday",
    "Saturday": "Saturday",
    "Sunday": "Sunday",
}

EMOJI_List = [
    "😶",
    "🙂",
    "😆",
    "😂",
    "😔",
    "😠",
    "😭",
    "😍",
    "😳",
    "😲",
    "😱",
    "🤔",
    "😉",
    "😎",
    "😌",
    "🤤",
    "😘",
    "😏",
    "😴",
    "😜",
    "🙄",
]


class PromptManager:
    """System prompt manager, responsible for managing and updating system prompts"""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or setup_logging()
        self.base_prompt_template = None
        self.last_update_time = 0

        # Import global cache manager
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType

        self._load_base_template()

    def _load_base_template(self):
        """Load base prompt template"""
        try:
            template_path = "agent-base-prompt.txt"
            cache_key = f"prompt_template:{template_path}"

            # Get from cache first
            cached_template = self.cache_manager.get(
                self.CacheType.CONFIG, cache_key)
            if cached_template is not None:
                self.base_prompt_template = cached_template
                self.logger.bind(tag=TAG).debug(
                    "Load base prompt template from cache")
                return

            # Cache miss, read from file
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # Store in cache (CONFIG type doesn't auto-expire by default, needs manual invalidation)
                self.cache_manager.set(
                    self.CacheType.CONFIG, cache_key, template_content
                )

                self.base_prompt_template = template_content
                self.logger.bind(tag=TAG).debug(
                    "Successfully loaded base prompt template and cached")
            else:
                self.logger.bind(tag=TAG).warning(
                    "agent-base-prompt.txt file not found")

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to load prompt template: {e}")

    def get_quick_prompt(self, user_prompt: str, device_id: str = None) -> str:
        """Quick get system prompt (using user configuration)"""
        device_cache_key = f"device_prompt:{device_id}"
        cached_device_prompt = self.cache_manager.get(
            self.CacheType.DEVICE_PROMPT, device_cache_key
        )

        if cached_device_prompt is not None:
            self.logger.bind(tag=TAG).debug(
                f"Using cached prompt for device {device_id}")
            return cached_device_prompt
        else:
            self.logger.bind(tag=TAG).debug(
                f"No cached prompt for device {device_id}, using passed prompt"
            )

        # Use passed prompt and cache (if device ID exists)
        if device_id:
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(self.CacheType.CONFIG,
                                   device_cache_key, user_prompt)
            self.logger.bind(tag=TAG).debug(
                f"Prompt for device {device_id} has been cached")

        self.logger.bind(tag=TAG).info(
            f"Using quick prompt: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self) -> tuple:
        """Get current time information"""
        from datetime import datetime

        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        today_weekday = WEEKDAY_MAP[now.strftime("%A")]
        today_lunar = cnlunar.Lunar(now, godType="8char")
        lunar_date = "%s年%s%s\n" % (
            today_lunar.lunarYearCn,
            today_lunar.lunarMonthCn[:-1],
            today_lunar.lunarDayCn,
        )

        return today_date, today_weekday, lunar_date

    def _get_location_info(self, client_ip: str) -> str:
        """Get location information"""
        try:
            # Get from cache first
            cached_location = self.cache_manager.get(
                self.CacheType.LOCATION, client_ip)
            if cached_location is not None:
                return cached_location

            # Cache miss, call API to get
            from core.utils.util import get_ip_info

            ip_info = get_ip_info(client_ip, self.logger)
            city = ip_info.get("city", "Unknown location")
            location = f"{city}"

            # Store in cache
            self.cache_manager.set(
                self.CacheType.LOCATION, client_ip, location)

            return location

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to get location information: {e}")
            return "Unknown location"

    def _get_weather_info(self, conn, location: str) -> str:
        """Get weather information"""
        try:
            # Get from cache first
            cached_weather = self.cache_manager.get(
                self.CacheType.WEATHER, location)
            if cached_weather is not None:
                return cached_weather

            # Cache miss, call get_weather function to get
            from plugins_func.functions.get_weather import get_weather
            from plugins_func.register import ActionResponse

            # Call get_weather function
            result = get_weather(conn, location=location, lang="zh_CN")
            if isinstance(result, ActionResponse):
                weather_report = result.result
                self.cache_manager.set(
                    self.CacheType.WEATHER, location, weather_report)
                return weather_report

            return "Failed to get weather information"

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to get weather information: {e}")
            return "Failed to get weather information"

    def update_context_info(self, conn, client_ip: str):
        """Synchronously update context information"""
        try:
            # Get location information (using global cache)
            local_address = self._get_location_info(client_ip)

            # Get weather information (using global cache)
            self._get_weather_info(conn, local_address)

            self.logger.bind(tag=TAG).info(
                f"Context information update completed")

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to update context information: {e}")

    def build_enhanced_prompt(
        self, user_prompt: str, device_id: str, client_ip: str = None
    ) -> str:
        """Build enhanced system prompt"""
        if not self.base_prompt_template:
            return user_prompt

        try:
            # Get latest time information (not cached)
            today_date, today_weekday, lunar_date = (
                self._get_current_time_info()
            )

            # Get cached context information
            local_address = ""
            weather_info = ""

            if client_ip:
                # Get location information (from global cache)
                local_address = (
                    self.cache_manager.get(
                        self.CacheType.LOCATION, client_ip) or ""
                )

                # Get weather information (from global cache)
                if local_address:
                    weather_info = (
                        self.cache_manager.get(
                            self.CacheType.WEATHER, local_address)
                        or ""
                    )

            # Replace template variables
            template = Template(self.base_prompt_template)
            enhanced_prompt = template.render(
                base_prompt=user_prompt,
                current_time="{{current_time}}",
                today_date=today_date,
                today_weekday=today_weekday,
                lunar_date=lunar_date,
                local_address=local_address,
                weather_info=weather_info,
                emojiList=EMOJI_List,
            )

            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, enhanced_prompt
            )

            self.logger.bind(tag=TAG).info(
                f"Built enhanced prompt successfully, length: {len(enhanced_prompt)}"
            )

            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to build enhanced prompt: {e}")
            return user_prompt
