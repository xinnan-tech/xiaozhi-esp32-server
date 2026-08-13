import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import jwt

from config.logger import setup_logging
from plugins_func.register import Action, ActionResponse, ToolType, register_function

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "获取某个地点的天气，用户应提供一个位置，比如用户说杭州天气，参数为：杭州。"
            "如果用户说的是省份，默认用省会城市。如果用户说的不是省份或城市而是一个地名，默认用该地所在省份的省会城市。"
            "重要：本地未来7天天气已在上下文中提供，用户未指明其他城市时绝对不要调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "地点名，例如杭州。可选参数，如果不提供则不传",
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN",
                },
            },
            "required": ["lang"],
        },
    },
}

REQUEST_TIMEOUT_SECONDS = 8.0
HTTP_TIMEOUT = httpx.Timeout(6.0, connect=3.0)
BASE_HEADERS = {
    "User-Agent": "xiaozhi-esp32-server/1.0",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}


class WeatherConfigError(ValueError):
    pass


class QWeatherApiError(RuntimeError):
    def __init__(self, operation: str, code: str):
        self.operation = operation
        self.code = code
        super().__init__(f"QWeather {operation} failed with code {code}")


def normalize_api_host(api_host: str) -> str:
    value = (api_host or "").strip().rstrip("/")
    if not value:
        raise WeatherConfigError("QWeather api_host is required")
    if not value.startswith(("https://", "http://")):
        value = "https://" + value
    return value


def normalize_language(lang: str) -> str:
    value = (lang or "zh_CN").replace("-", "_").lower()
    if value in {"zh_hk", "zh_tw", "zh_hant"}:
        return "zh-hant"
    return value.split("_", 1)[0]


def build_auth_headers(weather_config: dict, now: int | None = None) -> dict:
    headers = dict(BASE_HEADERS)
    auth_type = str(weather_config.get("auth_type") or "api_key").strip().lower()
    if auth_type == "api_key":
        api_key = str(weather_config.get("api_key") or "").strip()
        if not api_key:
            raise WeatherConfigError("QWeather api_key is required")
        headers["X-QW-Api-Key"] = api_key
        return headers
    if auth_type != "jwt":
        raise WeatherConfigError("QWeather auth_type must be api_key or jwt")

    project_id = str(weather_config.get("project_id") or "").strip()
    credential_id = str(weather_config.get("credential_id") or "").strip()
    private_key = str(weather_config.get("private_key") or "").strip()
    private_key_path = str(weather_config.get("private_key_path") or "").strip()
    if not private_key and private_key_path:
        try:
            private_key = Path(private_key_path).read_text(encoding="utf-8").strip()
        except OSError as exception:
            raise WeatherConfigError("QWeather private_key_path cannot be read") from exception
    if not project_id or not credential_id or not private_key:
        raise WeatherConfigError("QWeather JWT credentials are incomplete")

    issued_at = int(time.time()) if now is None else int(now)
    try:
        token = jwt.encode(
            {
                "sub": project_id,
                "iat": issued_at - 30,
                "exp": issued_at + 900,
            },
            private_key,
            algorithm="EdDSA",
            headers={"kid": credential_id},
        )
    except Exception as exception:
        raise WeatherConfigError("QWeather JWT could not be generated") from exception
    headers["Authorization"] = f"Bearer {token}"
    return headers


async def _request_json(
    client: httpx.AsyncClient,
    url: str,
    operation: str,
    headers: dict,
    params: dict,
) -> dict:
    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    code = str(data.get("code") or "")
    if code != "200":
        raise QWeatherApiError(operation, code or "unknown")
    return data


async def fetch_weather_data(
    weather_config: dict,
    location: str,
    lang: str,
    client: httpx.AsyncClient | None = None,
) -> tuple[dict | None, dict, dict]:
    base_url = normalize_api_host(weather_config.get("api_host"))
    headers = build_auth_headers(weather_config)
    qweather_lang = normalize_language(lang)

    async def fetch(active_client: httpx.AsyncClient):
        city_data = await _request_json(
            active_client,
            f"{base_url}/geo/v2/city/lookup",
            "city lookup",
            headers,
            {"location": location, "lang": qweather_lang, "number": 1},
        )
        locations = city_data.get("location") or []
        if not locations:
            return None, {}, {}
        city = locations[0]
        location_id = city.get("id")
        if not location_id:
            return None, {}, {}
        common_params = {"location": location_id, "lang": qweather_lang}
        current_task = _request_json(
            active_client,
            f"{base_url}/v7/weather/now",
            "current weather",
            headers,
            common_params,
        )
        daily_task = _request_json(
            active_client,
            f"{base_url}/v7/weather/7d",
            "daily forecast",
            headers,
            common_params,
        )
        current, daily = await asyncio.gather(current_task, daily_task)
        return city, current, daily

    async def run():
        if client is not None:
            return await fetch(client)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as active_client:
            return await fetch(active_client)

    return await asyncio.wait_for(run(), timeout=REQUEST_TIMEOUT_SECONDS)


def format_weather_report(city: dict, current_data: dict, daily_data: dict) -> str:
    city_name = city.get("name") or "未知"
    current = current_data.get("now") or {}
    weather_text = current.get("text") or "未知"
    temperature = current.get("temp")
    feels_like = current.get("feelsLike")

    summary_parts = [weather_text]
    if temperature is not None:
        summary_parts.append(f"{temperature}℃")
    if feels_like is not None:
        summary_parts.append(f"体感 {feels_like}℃")
    report = f"您查询的位置是：{city_name}\n\n当前天气: " + "，".join(summary_parts) + "\n"

    details = []
    for label, key, suffix in (
        ("湿度", "humidity", "%"),
        ("风向", "windDir", ""),
        ("风力", "windScale", "级"),
        ("风速", "windSpeed", "公里/小时"),
        ("能见度", "vis", "公里"),
        ("气压", "pressure", "百帕"),
        ("降水量", "precip", "毫米"),
    ):
        value = current.get(key)
        if value not in (None, ""):
            details.append(f"  · {label}: {value}{suffix}")
    if details:
        report += "详细参数：\n" + "\n".join(details) + "\n"

    report += "\n未来7天预报：\n"
    for day in (daily_data.get("daily") or [])[:7]:
        day_text = day.get("textDay") or "未知"
        night_text = day.get("textNight") or ""
        if night_text and night_text != day_text:
            day_text = f"{day_text}转{night_text}"
        report += (
            f"{day.get('fxDate', '未知日期')}: {day_text}，"
            f"气温 {day.get('tempMin', '?')}~{day.get('tempMax', '?')}℃\n"
        )
    return report + "\n（如需某一天的具体天气，请告诉我日期）"


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def get_weather(conn: "ConnectionHandler", location: str = None, lang: str = "zh_CN"):
    from core.utils.cache.manager import CacheType, cache_manager
    from core.utils.util import get_ip_info

    weather_config = conn.config.get("plugins", {}).get("get_weather", {})
    default_location = weather_config.get("default_location", "广州")
    client_ip = conn.client_ip

    if not location:
        if client_ip:
            cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
            if cached_ip_info:
                location = cached_ip_info.get("city")
            else:
                ip_info = get_ip_info(client_ip, logger)
                if ip_info:
                    cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
                    location = ip_info.get("city")
        location = location or default_location

    weather_cache_key = f"full_weather_{location}_{normalize_language(lang)}"
    cached_weather_report = cache_manager.get(CacheType.WEATHER, weather_cache_key)
    if cached_weather_report:
        return ActionResponse(Action.REQLLM, cached_weather_report, None)

    try:
        city, current, daily = await fetch_weather_data(weather_config, location, lang)
    except WeatherConfigError:
        logger.bind(tag=TAG).warning("QWeather authentication configuration is incomplete")
        return ActionResponse(Action.REQLLM, None, "天气服务认证配置不完整")
    except (QWeatherApiError, httpx.HTTPError, asyncio.TimeoutError) as exception:
        logger.bind(tag=TAG).warning(f"QWeather request failed: {type(exception).__name__}")
        return ActionResponse(Action.REQLLM, None, "天气服务请求失败，请稍后再试")

    if not city:
        return ActionResponse(
            Action.REQLLM, f"未找到相关的城市: {location}，请确认地点是否正确", None
        )
    weather_report = format_weather_report(city, current, daily)
    cache_manager.set(CacheType.WEATHER, weather_cache_key, weather_report)
    return ActionResponse(Action.REQLLM, weather_report, None)
