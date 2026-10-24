import asyncio
import datetime
import re
import httpx
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info
from typing import TYPE_CHECKING

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    )
}

# 仓库里不再预置和风天气的凭据，自己部署的人得自己去申请一个
WEATHER_CREDENTIAL_HINT = (
    "尚未配置和风天气 api_key，请参考 docs/weather-integration.md 申请后填入"
)
WEATHER_HOST_HINT = (
    "尚未配置和风天气 api_host，请参考 docs/weather-integration.md 申请后填入"
)

# 上游挂着的时候每次提问都要把整条链路重走一遍，用户要等二十几秒。
# 失败结果短时间内不会变，先记下来直接回
WEATHER_FAILURE_TTL = 300

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 网页上写的是符号单位，报告里统一用中文，两条路径读出来的东西才对得上
UNIT_NAMES = {
    "km/h": "公里/小时",
    "km": "公里",
    "mm": "毫米",
    "hpa": "百帕",
    "°": "℃",
    "°c": "℃",
}

# 网页上的参数名和接口返回的不一样，报告里用接口那套
ITEM_NAMES = {
    "大气压": "气压",
    "相对湿度": "湿度",
}

# 天气代码 https://dev.qweather.com/docs/resource/icons/#weather-icons
WEATHER_CODE_MAP = {
    "100": "晴",
    "101": "多云",
    "102": "少云",
    "103": "晴间多云",
    "104": "阴",
    "150": "晴",
    "151": "多云",
    "152": "少云",
    "153": "晴间多云",
    "300": "阵雨",
    "301": "强阵雨",
    "302": "雷阵雨",
    "303": "强雷阵雨",
    "304": "雷阵雨伴有冰雹",
    "305": "小雨",
    "306": "中雨",
    "307": "大雨",
    "308": "极端降雨",
    "309": "毛毛雨/细雨",
    "310": "暴雨",
    "311": "大暴雨",
    "312": "特大暴雨",
    "313": "冻雨",
    "314": "小到中雨",
    "315": "中到大雨",
    "316": "大到暴雨",
    "317": "暴雨到大暴雨",
    "318": "大暴雨到特大暴雨",
    "350": "阵雨",
    "351": "强阵雨",
    "399": "雨",
    "400": "小雪",
    "401": "中雪",
    "402": "大雪",
    "403": "暴雪",
    "404": "雨夹雪",
    "405": "雨雪天气",
    "406": "阵雨夹雪",
    "407": "阵雪",
    "408": "小到中雪",
    "409": "中到大雪",
    "410": "大到暴雪",
    "456": "阵雨夹雪",
    "457": "阵雪",
    "499": "雪",
    "500": "薄雾",
    "501": "雾",
    "502": "霾",
    "503": "扬沙",
    "504": "浮尘",
    "507": "沙尘暴",
    "508": "强沙尘暴",
    "509": "浓雾",
    "510": "强浓雾",
    "511": "中度霾",
    "512": "重度霾",
    "513": "严重霾",
    "514": "大雾",
    "515": "特强浓雾",
    "900": "热",
    "901": "冷",
    "999": "未知",
}


def format_observation_time(raw_time):
    """观测时间接口给的是带 T 的写法，报告里换成空格好看点"""
    if not raw_time:
        return None
    return str(raw_time).replace("T", " ", 1)


def format_forecast_date(raw_date, today=None):
    """
    预报日期统一成 今天/明天/后天 或者 星期加月日

    <p>
    接口给的是 2026-10-24 这种写法，网页上写的是 今天10月24日，
    两条路径各写各的，用户听不出来是同一份数据。统一成一种写法。
    """
    if not raw_date:
        return raw_date
    text = str(raw_date).strip()
    today = today or datetime.date.today()

    iso = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso:
        year = int(iso.group(1))
        month = int(iso.group(2))
        day = int(iso.group(3))
    else:
        found = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if not found:
            return text
        year = today.year
        month = int(found.group(1))
        day = int(found.group(2))

    try:
        date_value = datetime.date(year, month, day)
    except ValueError:
        return text

    delta = (date_value - today).days
    if delta == 0:
        prefix = "今天"
    elif delta == 1:
        prefix = "明天"
    elif delta == 2:
        prefix = "后天"
    else:
        prefix = WEEKDAY_NAMES[date_value.weekday()]
    return f"{prefix}{month}月{day}日"


def normalize_unit(value):
    """把单位符号换成中文写法，换不动就原样留着"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return text
    matched = re.fullmatch(r"(.+?)([a-zA-Z°℃/]+)", text)
    if not matched:
        return text
    unit = matched.group(2).lower()
    if unit not in UNIT_NAMES:
        return text
    return f"{matched.group(1)}{UNIT_NAMES[unit]}"


def normalize_temperature(value):
    """温度只留数值，单位在报告里统一写一次"""
    if value is None:
        return None
    matched = re.match(r"-?\d+(?:\.\d+)?", str(value).strip())
    return matched.group(0) if matched else None


def normalize_wind_scale(value):
    """风力统一成 3级 这种带单位的写法"""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.endswith("级"):
        return text
    return f"{text}级"


async def fetch_city_info(location, api_key, api_host):
    url = f"https://{api_host}/geo/v2/city/lookup"
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        response = await client.get(
            url,
            params={
                "key": api_key,
                "location": location,
                "lang": "zh",
                "number": 1,
            },
            headers=HEADERS,
        )
    try:
        data = response.json()
    except ValueError:
        logger.bind(tag=TAG).error(
            f"获取天气城市失败：HTTP {response.status_code} 返回了非 JSON 内容"
        )
        return None
    if not isinstance(data, dict):
        logger.bind(tag=TAG).error("获取天气城市失败：响应不是 JSON 对象")
        return None
    if response.status_code != 200 or data.get("code") != "200":
        logger.bind(tag=TAG).error(
            f"获取天气城市失败：HTTP {response.status_code}，代码 {data.get('code')}"
        )
        return None
    return data.get("location", [])[0] if data.get("location") else None


async def fetch_weather_data(city_info, api_key, api_host):
    location_id = city_info.get("id")
    if not location_id:
        return None

    base_url = f"https://{api_host}/v7/weather"
    params = {"key": api_key, "location": location_id, "lang": "zh"}

    async def request(client, endpoint):
        response = await client.get(f"{base_url}/{endpoint}", params=params, headers=HEADERS)
        try:
            data = response.json()
        except ValueError:
            return None
        if response.status_code != 200 or data.get("code") != "200":
            logger.bind(tag=TAG).error(
                f"获取天气数据失败：接口={endpoint} HTTP {response.status_code}，代码 {data.get('code')}"
            )
            return None
        return data

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
            now, daily = await asyncio.gather(
                request(client, "now"), request(client, "7d")
            )
    except Exception as e:
        logger.bind(tag=TAG).warning(f"获取天气 JSON 接口失败，将尝试网页接口: {e}")
        return None
    if now is None or daily is None:
        return None
    return now, daily


def format_weather_report(
    city_name, current_text, current_basic, temps_list, observed_at=None
):
    """两条路径的报告走同一个模板，日期和单位的写法才对得上"""
    weather_report = f"您查询的位置是：{city_name}\n\n当前天气: {current_text}\n"
    if observed_at:
        weather_report += f"观测时间：{observed_at}\n"

    if current_basic:
        weather_report += "详细参数：\n"
        weather_report += "".join(
            f"  · {key}: {value}\n" for key, value in current_basic.items()
        )

    weather_report += "\n未来7天预报：\n"
    weather_report += "".join(
        f"{date}: {weather}，气温 {low}~{high}℃\n"
        for date, weather, high, low in temps_list
    )
    weather_report += "\n（如需某一天的具体天气，请告诉我日期）"
    return weather_report


def build_weather_report(city_info, now_data, daily_data):
    city_name = city_info.get("name") or city_info.get("adm2") or "未知位置"
    now = now_data.get("now", {})

    current_basic = {
        "温度": f"{now['temp']}℃" if now.get("temp") is not None else None,
        "体感温度": f"{now['feelsLike']}℃" if now.get("feelsLike") is not None else None,
        "湿度": f"{now['humidity']}%" if now.get("humidity") is not None else None,
        "风向": now.get("windDir"),
        "风力": normalize_wind_scale(now.get("windScale")),
        "能见度": f"{now['vis']}公里" if now.get("vis") is not None else None,
        "气压": f"{now['pressure']}百帕" if now.get("pressure") is not None else None,
        "降水量": f"{now['precip']}毫米" if now.get("precip") is not None else None,
    }
    current_basic = {key: value for key, value in current_basic.items() if value}

    temps_list = []
    for item in daily_data.get("daily", [])[:7]:
        date = format_forecast_date(item.get("fxDate") or "未知日期")
        weather = item.get("textDay") or WEATHER_CODE_MAP.get(item.get("iconDay"), "未知")
        high = normalize_temperature(item.get("tempMax")) or "未知"
        low = normalize_temperature(item.get("tempMin")) or "未知"
        temps_list.append((date, weather, high, low))

    # 观测时间在 now.obsTime 里，now.updateTime 是空的，兜底才用响应顶层那个
    observed_at = format_observation_time(
        now.get("obsTime") or now_data.get("updateTime")
    )
    return format_weather_report(
        city_name, now.get("text", "未知"), current_basic, temps_list, observed_at
    )


async def fetch_weather_page(url):
    # 网页只是兜底，等太久不值得，接口那边不通的话很快就该告诉用户
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=3.0), follow_redirects=True
    ) as client:
        response = await client.get(url, headers=HEADERS)
    return BeautifulSoup(response.text, "html.parser") if response.status_code == 200 else None


def parse_weather_info(soup):
    """
    解析和风天气网页上的天气

    <p>
    页面的结构一变，取不到元素就返回 None。抛异常的话 Python 的原文
    会被当成回复内容念给用户，听着像系统在报错。
    """
    if soup is None:
        return None

    city_element = soup.select_one("h1.c-submenu__location")
    if city_element is None:
        logger.bind(tag=TAG).warning("网页天气解析失败：取不到城市名")
        return None
    city_name = city_element.get_text(strip=True)

    current_abstract = soup.select_one(".c-city-weather-current .current-abstract")
    current_abstract = (
        current_abstract.get_text(strip=True) if current_abstract else "未知"
    )

    current_basic = {}
    for item in soup.select(
        ".c-city-weather-current .current-basic .current-basic___item"
    ):
        parts = item.get_text(strip=True, separator=" ").split(" ")
        if len(parts) == 2:
            key, value = parts[1], parts[0]
            # 风向和风力挤在一项里，拆成两项跟接口那套对上
            if key.endswith("风") and value.endswith("级"):
                current_basic["风向"] = key
                current_basic["风力"] = value
                continue
            key = ITEM_NAMES.get(key, key)
            value = normalize_unit(value)
            if not value or value == "0":
                continue
            current_basic[key] = value

    temps_list = []
    for row in soup.select(".city-forecast-tabs__row")[:7]:  # 取前7天的数据
        date_element = row.select_one(".date-bg .date")
        icon_element = row.select_one(".date-bg .icon")
        if date_element is None or icon_element is None:
            logger.bind(tag=TAG).warning("网页天气解析失败：预报行缺日期或图标")
            return None
        icon_src = icon_element.get("src")
        if not icon_src:
            logger.bind(tag=TAG).warning("网页天气解析失败：预报行图标没有地址")
            return None
        weather_code = icon_src.split("/")[-1].split(".")[0]
        weather = WEATHER_CODE_MAP.get(weather_code, "未知")
        temps = [span.get_text(strip=True) for span in row.select(".tmp-cont .temp")]
        high_temp, low_temp = (temps[0], temps[-1]) if len(temps) >= 2 else (None, None)
        temps_list.append(
            (
                format_forecast_date(date_element.get_text(strip=True)),
                weather,
                normalize_temperature(high_temp) or "未知",
                normalize_temperature(low_temp) or "未知",
            )
        )

    return city_name, current_abstract, current_basic, temps_list


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def get_weather(conn: "ConnectionHandler", location: str = None, lang: str = "zh_CN"):
    from core.utils.cache.manager import cache_manager, CacheType

    weather_config = conn.config.get("plugins", {}).get("get_weather", {})
    api_key = str(weather_config.get("api_key") or "").strip()
    api_host = str(weather_config.get("api_host") or "").strip()
    default_location = weather_config.get("default_location", "广州")
    client_ip = conn.client_ip

    # 凭据没配就没法取数据，直接告诉用户去申请，别拿空 key 去撞接口
    if not api_key:
        return ActionResponse(Action.REQLLM, WEATHER_CREDENTIAL_HINT, None)
    if not api_host:
        return ActionResponse(Action.REQLLM, WEATHER_HOST_HINT, None)

    # 优先使用用户提供的location参数
    if not location:
        # 通过客户端IP解析城市
        if client_ip:
            # 先从缓存获取IP对应的城市信息
            cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
            if cached_ip_info:
                location = cached_ip_info.get("city")
            else:
                # 缓存未命中，调用API获取
                ip_info = get_ip_info(client_ip, logger)
                if ip_info:
                    cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
                    location = ip_info.get("city")

            if not location:
                location = default_location
        else:
            # 若无IP，使用默认位置
            location = default_location
    # 尝试从缓存获取完整天气报告
    weather_cache_key = f"full_weather_{location}_{lang}"
    failure_cache_key = f"failed_weather_{location}_{lang}"
    cached_weather_report = cache_manager.get(CacheType.WEATHER, weather_cache_key)
    if cached_weather_report:
        return ActionResponse(Action.REQLLM, cached_weather_report, None)
    # 刚失败过就不要再走一遍链路，用户等不起
    cached_failure = cache_manager.get(CacheType.WEATHER, failure_cache_key)
    if cached_failure:
        return ActionResponse(Action.REQLLM, cached_failure, None)

    # 缓存未命中，获取实时天气数据
    city_info = await fetch_city_info(location, api_key, api_host)
    if not city_info:
        message = f"暂时查不到 {location} 的天气（城市未找到或天气服务不可用），请稍后再试"
        cache_manager.set(
            CacheType.WEATHER, failure_cache_key, message, ttl=WEATHER_FAILURE_TTL
        )
        return ActionResponse(Action.REQLLM, message, None)
    weather_data = await fetch_weather_data(city_info, api_key, api_host)
    if weather_data:
        weather_report = build_weather_report(city_info, *weather_data)
    else:
        fx_link = city_info.get("fxLink")
        soup = await fetch_weather_page(fx_link) if fx_link else None
        parsed = parse_weather_info(soup)
        if not parsed:
            message = "暂时查不到天气数据，请稍后再试"
            cache_manager.set(
                CacheType.WEATHER, failure_cache_key, message, ttl=WEATHER_FAILURE_TTL
            )
            return ActionResponse(Action.REQLLM, message, "请求天气数据失败")
        city_name, current_abstract, current_basic, temps_list = parsed
        weather_report = format_weather_report(
            city_name, current_abstract, current_basic, temps_list
        )

    # 缓存完整的天气报告
    cache_manager.set(CacheType.WEATHER, weather_cache_key, weather_report)

    return ActionResponse(Action.REQLLM, weather_report, None)
