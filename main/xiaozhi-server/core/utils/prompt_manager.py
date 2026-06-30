"""
系统提示词管理器模块
负责管理和更新系统提示词，包括快速初始化和异步增强功能
"""

import os
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from config.logger import setup_logging
from jinja2 import Template

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
        self.base_prompt_template = None
        self.last_update_time = 0

        # 导入全局缓存管理器
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType

        # 初始化上下文源
        from core.utils.context_provider import ContextDataProvider

        self.context_provider = ContextDataProvider(config, self.logger)
        self.context_data = {}

        self._load_base_template()

    def _load_base_template(self):
        """加载基础提示词模板"""
        try:
            template_path = self.config.get("prompt_template", None)
            if not template_path:
                template_path = "agent-base-prompt.txt"
            cache_key = f"prompt_template:{template_path}"

            # 先从缓存获取
            cached_template = self.cache_manager.get(self.CacheType.CONFIG, cache_key)
            if cached_template is not None:
                self.base_prompt_template = cached_template
                self.logger.bind(tag=TAG).debug("从缓存加载基础提示词模板")
                return

            # 缓存未命中，从文件读取
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # 存入缓存（CONFIG类型默认不自动过期，需要手动失效）
                self.cache_manager.set(
                    self.CacheType.CONFIG, cache_key, template_content
                )
                self.base_prompt_template = template_content
                self.logger.bind(tag=TAG).debug("成功加载基础提示词模板并缓存")
            else:
                self.logger.bind(tag=TAG).warning(f"未找到{template_path}文件")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"加载提示词模板失败: {e}")

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
            self.cache_manager.set(self.CacheType.DEVICE_PROMPT, device_cache_key, user_prompt)
            self.logger.bind(tag=TAG).debug(f"设备 {device_id} 的提示词已缓存")

        self.logger.bind(tag=TAG).info(f"使用快速提示词: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self) -> tuple:
        """获取当前时间信息"""
        from .current_time import (
            get_current_date,
            get_current_weekday,
            get_current_lunar_date,
        )

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

    def _get_weather_info(self, conn: "ConnectionHandler", location: str) -> str:
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
            local_address = ""
            if (
                client_ip
                and self.base_prompt_template
                and (
                    "local_address" in self.base_prompt_template
                    or "weather_info" in self.base_prompt_template
                )
            ):
                # 获取位置信息（使用全局缓存）
                local_address = self._get_location_info(client_ip)

            if (
                self.base_prompt_template
                and "weather_info" in self.base_prompt_template
                and local_address
            ):
                # 获取天气信息（使用全局缓存）
                self._get_weather_info(conn, local_address)

            # 获取配置的上下文数据
            if hasattr(conn, "device_id") and conn.device_id:
                if (
                    self.base_prompt_template
                    and "dynamic_context" in self.base_prompt_template
                ):
                    self.context_data = self.context_provider.fetch_all(conn.device_id)
                else:
                    self.context_data = ""

            self.logger.bind(tag=TAG).debug(f"上下文信息更新完成")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新上下文信息失败: {e}")

    def build_enhanced_prompt(
        self, user_prompt: str, device_id: str, client_ip: str = None, *args, **kwargs
    ) -> str:
        """构建增强的系统提示词"""
        if not self.base_prompt_template:
            return user_prompt

        try:
            # 获取最新的时间信息（不缓存）
            today_date, today_weekday, lunar_date = self._get_current_time_info()

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

            # 获取TTS选择的语言，默认值为中文
            language = kwargs.get("device_language")
            if not language:
                language = (
                    self.config.get("TTS", {})
                    .get(self.config.get("selected_module", {}).get("TTS", ""), {})
                    .get("language")
                    or "中文"
                )
            self.logger.bind(tag=TAG).debug(f"获取到选择的语言: {language}")

            # 替换模板变量
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
                device_id=device_id,
                client_ip=client_ip,
                dynamic_context=self.context_data,
                language=language,
                *args,
                **kwargs,
            )
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, enhanced_prompt
            )
            self.logger.bind(tag=TAG).info(
                f"构建增强提示词成功，长度: {len(enhanced_prompt)}"
            )
            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"构建增强提示词失败: {e}")
            return user_prompt
