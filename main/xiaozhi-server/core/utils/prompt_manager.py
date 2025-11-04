"""
系统提示词管理器模块
负责管理和更新系统提示词，包括快速初始化和异步增强功能
使用新的模块化架构构建系统提示词
"""

import os
from typing import Dict, Any, Optional
from config.logger import setup_logging

TAG = __name__

WEEKDAY_MAP = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
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
    """系统提示词管理器，负责管理和更新系统提示词"""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or setup_logging()
        self.last_update_time = 0

        # 导入全局缓存管理器
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType

    def get_quick_prompt(self, user_prompt: str, device_id: str = None) -> str:
        """快速获取系统提示词（使用用户配置）"""
        device_cache_key = f"device_prompt:{device_id}"
        cached_device_prompt = self.cache_manager.get(
            self.CacheType.DEVICE_PROMPT, device_cache_key
        )
        if cached_device_prompt is not None:
            self.logger.bind(tag=TAG).debug(f"使用设备 {device_id} 的缓存提示词")
            return cached_device_prompt
        else:
            self.logger.bind(tag=TAG).debug(
                f"设备 {device_id} 无缓存提示词，使用传入的提示词"
            )

        # 使用传入的提示词并缓存（如果有设备ID）
        if device_id:
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(self.CacheType.CONFIG, device_cache_key, user_prompt)
            self.logger.bind(tag=TAG).debug(f"设备 {device_id} 的提示词已缓存")

        self.logger.bind(tag=TAG).info(f"使用快速提示词: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self) -> tuple:
        """获取当前时间信息"""
        from .current_time import get_current_date, get_current_weekday, get_current_lunar_date
        
        today_date = get_current_date()
        today_weekday = get_current_weekday()
        lunar_date = get_current_lunar_date() + "\n"

        return today_date, today_weekday, lunar_date

    def _get_location_info(self, client_ip: str) -> str:
        """获取位置信息"""
        try:
            # 先从缓存获取
            cached_location = self.cache_manager.get(self.CacheType.LOCATION, client_ip)
            if cached_location is not None:
                return cached_location

            # 缓存未命中，调用API获取
            from core.utils.util import get_ip_info

            ip_info = get_ip_info(client_ip, self.logger)
            city = ip_info.get("city", "未知位置")
            location = f"{city}"

            # 存入缓存
            self.cache_manager.set(self.CacheType.LOCATION, client_ip, location)
            return location
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取位置信息失败: {e}")
            return "未知位置"

    def _get_weather_info(self, conn, location: str) -> str:
        """获取天气信息"""
        try:
            # 先从缓存获取
            cached_weather = self.cache_manager.get(self.CacheType.WEATHER, location)
            if cached_weather is not None:
                return cached_weather

            # 缓存未命中，调用get_weather函数获取
            from plugins_func.functions.get_weather import get_weather
            from plugins_func.register import ActionResponse

            # 调用get_weather函数
            result = get_weather(conn, location=location, lang="zh_CN")
            if isinstance(result, ActionResponse):
                weather_report = result.result
                self.cache_manager.set(self.CacheType.WEATHER, location, weather_report)
                return weather_report
            return "天气信息获取失败"

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取天气信息失败: {e}")
            return "天气信息获取失败"

    def update_context_info(self, conn, client_ip: str):
        """同步更新上下文信息"""
        try:
            # 获取位置信息（使用全局缓存）
            local_address = self._get_location_info(client_ip)
            # 获取天气信息（使用全局缓存）
            self._get_weather_info(conn, local_address)
            self.logger.bind(tag=TAG).info(f"上下文信息更新完成")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新上下文信息失败: {e}")

    def build_enhanced_prompt(
        self,
        user_prompt: str,
        device_id: str,
        client_ip: str = None,
        user_persona: str = None,
        *args,
        **kwargs
    ) -> str:
        """构建增强的系统提示词（使用新的模块化架构）"""
        try:
            from core.roles.prompts.builder import build_system_prompt
            from core.roles import get_role_config_loader
            
            # 优先级：API 传入的 user_prompt > 本地 role 配置 > 空字符串
            if user_prompt and user_prompt.strip():
                # 优先使用 API 传入的 prompt（正式部署场景）
                profile = user_prompt
                timezone = self.config.get("timezone", "Asia/Shanghai")
                language = self.config.get("language", "zh")
                self.logger.bind(tag=TAG).info("使用 API 下发的 profile")
            else:
                # API 未提供 prompt，尝试加载本地 role 配置（本地开发场景）
                role_id = self.config.get("role_id", "default")
                loader = get_role_config_loader()
                
                try:
                    role_config = loader.load(role_id)
                    profile = role_config.profile
                    timezone = role_config.timezone
                    language = role_config.language
                    self.logger.bind(tag=TAG).info(f"使用本地 role 配置: {role_id}")
                except Exception as e:
                    # 兜底方案：使用空 profile
                    self.logger.bind(tag=TAG).warning(f"加载 role 配置失败: {e}，使用空 profile")
                    profile = ""
                    timezone = self.config.get("timezone", "Asia/Shanghai")
                    language = self.config.get("language", "zh")
            
            # 获取最新的时间信息（不缓存）
            today_date, today_weekday, lunar_date = self._get_current_time_info()
            # 清理 lunar_date 的换行符
            lunar_date = lunar_date.strip() if lunar_date else None

            # 获取缓存的上下文信息
            local_address = ""
            weather_info = ""

            if client_ip:
                # 获取位置信息（从全局缓存）
                local_address = (
                    self.cache_manager.get(self.CacheType.LOCATION, client_ip) or ""
                )

                # 获取天气信息（从全局缓存）
                if local_address:
                    weather_info = (
                        self.cache_manager.get(self.CacheType.WEATHER, local_address)
                        or ""
                    )

            # 使用新的模块化架构构建 prompt
            enhanced_prompt = build_system_prompt(
                profile=profile,
                timezone=timezone,
                language=language,
                user_persona=user_persona,
                today_date=today_date,
                today_weekday=today_weekday,
                lunar_date=lunar_date,
                local_address=local_address,
                weather_info=weather_info,
                device_id=device_id,
                **kwargs
            )
            
            # 缓存增强后的 prompt
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, enhanced_prompt
            )
            
            self.logger.bind(tag=TAG).info(
                f"构建增强提示词成功，长度: {len(enhanced_prompt)}"
            )
            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"构建增强提示词失败: {e}", exc_info=True)
            return user_prompt
