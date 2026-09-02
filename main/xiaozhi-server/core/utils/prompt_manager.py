"""
System prompt manager module
Responsible for managing and updating system prompts, including quick initialization and async enhancement functions
"""

import os
from typing import Dict, Any
from config.logger import setup_logging
from config.config_loader import get_project_dir
from jinja2 import Template

TAG = __name__

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
        
        # Initialize context source
        from core.utils.context_provider import ContextDataProvider
        self.context_provider = ContextDataProvider(config, self.logger)
        self.context_data = {}

        self._load_base_template()

    def _load_base_template(self):
        """Load base prompt template"""
        try:
            template_path = self.config.get("prompt_template", "data/agent-base-prompt.txt")
            if not os.path.isabs(template_path):
                template_path = os.path.join(get_project_dir(), template_path)
            cache_key = f"prompt_template:{template_path}"

            # Try cache first
            cached_template = self.cache_manager.get(self.CacheType.CONFIG, cache_key)
            if cached_template is not None:
                self.base_prompt_template = cached_template
                self.logger.bind(tag=TAG).debug("Load base prompt template from cache")
                return

            # Cache miss, read from file
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # Save to cache (CONFIG type does not expire automatically, needs manual invalidation)
                self.cache_manager.set(
                    self.CacheType.CONFIG, cache_key, template_content
                )
                self.base_prompt_template = template_content
                self.logger.bind(tag=TAG).debug("Successfully loaded base prompt template and cached")
            else:
                self.logger.bind(tag=TAG).warning(f"File {template_path} not found")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to load prompt template: {e}")

    def get_quick_prompt(self, user_prompt: str, device_id: str = None, client_id: str = None) -> str:
        """Quickly get system prompt (use user config or device-specific override)"""
        
        # 1. Check for file-based override: data/{client_id}/prompt.txt
        # Check client_id first (more specific session), then device_id (hardware)
        target_ids = []
        if client_id: target_ids.append(client_id)
        if device_id: target_ids.append(device_id)
        
        for tid in target_ids:
            # Modified Logic: data/{client_id}/prompt.txt
            prompt_file = os.path.join("data", tid, "prompt.txt")
            if os.path.exists(prompt_file):
                try:
                    with open(prompt_file, "r", encoding="utf-8") as f:
                        file_prompt = f.read().strip()
                        if file_prompt:
                            self.logger.bind(tag=TAG).info(f"Loaded device-specific prompt from {prompt_file}")
                            return file_prompt
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to load prompt file {prompt_file}: {e}")
            
            # Legacy Fallback: check data/prompts/{tid}.txt
            legacy_file = os.path.join("data", "prompts", f"{tid}.txt")
            if os.path.exists(legacy_file):
                try:
                    with open(legacy_file, "r", encoding="utf-8") as f:
                        file_prompt = f.read().strip()
                        if file_prompt:
                            self.logger.bind(tag=TAG).info(f"Loaded legacy device-specific prompt from {legacy_file}")
                            return file_prompt
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to load legacy prompt file {legacy_file}: {e}")

        # 2. Check Device Cache (using device_id as primary key)
        # Note: if client_id is provided but not device_id, we might want to cache by client_id too, 
        # but existing logic uses device_id extensively.
        cache_key_id = device_id or client_id
        device_cache_key = f"device_prompt:{cache_key_id}" if cache_key_id else None
        
        if device_cache_key:
            cached_device_prompt = self.cache_manager.get(
                self.CacheType.DEVICE_PROMPT, device_cache_key
            )
            if cached_device_prompt is not None:
                self.logger.bind(tag=TAG).debug(f"Using cached prompt for {cache_key_id}")
                return cached_device_prompt

        # 3. Fallback to default user_prompt
        self.logger.bind(tag=TAG).debug(
            f"No specific prompt for {cache_key_id}, using provided default"
        )

        # Cache provided prompt if device ID exists
        if device_id:
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(self.CacheType.CONFIG, device_cache_key, user_prompt)

        self.logger.bind(tag=TAG).info(f"Using default prompt: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self) -> tuple:
        """Get current time info"""
        from .current_time import (
            get_current_date,
            get_current_weekday,
            get_current_lunar_date,
        )

        today_date = get_current_date()
        today_weekday = get_current_weekday()
        lunar_date = get_current_lunar_date() + "\n"

        return today_date, today_weekday, lunar_date

    def _get_location_info(self, client_ip: str, client_id: str = None) -> str:
        """Get location info (prefer IP, fallback to client config)"""
        try:
            # 1. Try cache for IP-based location
            cached_location = self.cache_manager.get(self.CacheType.LOCATION, client_ip)
            if cached_location is not None:
                return cached_location

            # 2. Try IP Geolocation
            from core.utils.util import get_ip_info

            ip_info = get_ip_info(client_ip, self.logger)
            city = ip_info.get("city")
            
            if city and city != "Unknown location":
                location = f"{city}"
                # Save to cache
                self.cache_manager.set(self.CacheType.LOCATION, client_ip, location)
                return location

            # 3. Fallback to Client Configuration if IP geo fails or is uncertain
            if client_id:
                client_config_path = os.path.join("data", client_id, "config.json")
                if os.path.exists(client_config_path):
                    try:
                        import json
                        with open(client_config_path, "r", encoding="utf-8") as f:
                            c = json.load(f)
                            client_location = c.get("default_location") or c.get("location")
                            if client_location:
                                self.logger.bind(tag=TAG).info(f"IP geo failed/Unknown, using client-specific fallback location: {client_location}")
                                return client_location
                    except Exception as e:
                        self.logger.bind(tag=TAG).warning(f"Failed to read client config for location: {e}")

            return "Unknown location"
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to get location info: {e}")
            return "Unknown location"

    def _get_weather_info(self, conn, location: str) -> str:
        """Get weather info"""
        try:
            # Try cache first
            cached_weather = self.cache_manager.get(self.CacheType.WEATHER, location)
            if cached_weather is not None:
                return cached_weather

            # Cache miss, call get_weather function to get
            from plugins_func.functions.get_weather import get_weather
            from plugins_func.register import ActionResponse

            # Call get_weather function
            result = get_weather(conn, location=location, lang="en_US")
            if isinstance(result, ActionResponse):
                weather_report = result.result
                self.cache_manager.set(self.CacheType.WEATHER, location, weather_report)
                return weather_report
            return "Failed to get weather info"

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to get weather info: {e}")
            return "Failed to get weather info"

    def update_context_info(self, conn, client_ip: str):
        """Sync update context info"""
        try:
            local_address = ""
            client_id = getattr(conn, "client_id", None)
            if not client_id and hasattr(conn, "headers") and conn.headers:
                client_id = conn.headers.get("client-id")

            if (
                (client_ip or client_id)
                and self.base_prompt_template
                and (
                    "local_address" in self.base_prompt_template
                    or "weather_info" in self.base_prompt_template
                )
            ):
                # Get location info (prefer client config)
                local_address = self._get_location_info(client_ip, client_id)

            if (
                self.base_prompt_template
                and "weather_info" in self.base_prompt_template
                and local_address
            ):
                # Get weather info (use global cache)
                self._get_weather_info(conn, local_address)
            
            # Get configured context data
            if hasattr(conn, "device_id") and conn.device_id:
                if self.base_prompt_template and "dynamic_context" in self.base_prompt_template:
                    self.context_data = self.context_provider.fetch_all(conn.device_id)
                else:
                    self.context_data = ""
                
            self.logger.bind(tag=TAG).debug(f"Context info update completed")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to update context info: {e}")

    def build_enhanced_prompt(
        self, user_prompt: str, device_id: str, client_ip: str = None, *args, **kwargs
    ) -> str:
        """Build enhanced system prompt"""
        if not self.base_prompt_template:
            return user_prompt

        # PREVENT NESTED IDENTITY TAGS
        # If user_prompt (from prompt.txt) already has <identity>, strip external template's tags
        template_str = self.base_prompt_template
        if "<identity>" in user_prompt:
            # Simple heuristic: if user_prompt has its own identity, 
            # we should not wrap it again in the template.
            # We strip the <identity> tags from the template for this render.
            template_str = template_str.replace("<identity>", "").replace("</identity>", "")

        try:
            # Get latest time info (no cache)
            today_date, today_weekday, lunar_date = self._get_current_time_info()

            # Get cached context info
            local_address = ""
            weather_info = ""

            # Try to get client_id from kwargs (passed from Connection)
            client_id = kwargs.get("client_id")

            if client_ip or client_id:
                # Get location info (resolves client config internally)
                local_address = self._get_location_info(client_ip, client_id)

                # Get weather info (from global cache)
                if local_address:
                    weather_info = (
                        self.cache_manager.get(self.CacheType.WEATHER, local_address)
                        or ""
                    )

            # Replace template variables
            template = Template(template_str)
            enhanced_prompt = template.render(
                base_prompt=user_prompt,
                current_time="{{current_time}}",
                today_date=today_date,
                today_weekday=today_weekday,
                lunar_date=lunar_date,
                local_address=local_address,
                weather_info=weather_info,
                emojiList=EMOJI_List,
                device_id=device_id,
                client_ip=client_ip,
                dynamic_context=self.context_data,
                *args,
                **kwargs,
            )
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, enhanced_prompt
            )
            self.logger.bind(tag=TAG).info(
                f"Enhanced prompt built successfully, length: {len(enhanced_prompt)}"
            )
            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to build enhanced prompt: {e}")
            return user_prompt
