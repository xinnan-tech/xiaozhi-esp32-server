import requests
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "获取某个地点的天气，用户应提供一个位置，比如用户说杭州天气，参数为：杭州。"
            "如果用户说的是省份，默认用省会城市。如果用户说的不是省份或城市而是一个地名，"
            "默认用该地所在省份的省会城市。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "地点名，例如杭州。可选参数，如果不提供则不传"
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN"
                }
            },
            "required": ["lang"]
        }
    }
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    )
}


def fetch_city_info(location, api_key):
    url = f"https://geoapi.qweather.com/v2/city/lookup?key={api_key}&location={location}&lang=zh"
    response = requests.get(url, headers=HEADERS).json()
    return response.get('location', [])[0] if response.get('location') else None


def fetch_weather_page(url):
    response = requests.get(url, headers=HEADERS)
    return BeautifulSoup(response.text, "html.parser") if response.ok else None


def parse_weather_info(soup):
    city_name = soup.select_one("h1.c-submenu__location").get_text(strip=True)

    current_abstract = soup.select_one(".c-city-weather-current .current-abstract")
    current_abstract = current_abstract.get_text(strip=True) if current_abstract else "未知"

    current_basic = {}
    for item in soup.select(".c-city-weather-current .current-basic .current-basic___item"):
        parts = item.get_text(strip=True, separator=" ").split(" ")
        if len(parts) == 2:
            key, value = parts[1], parts[0]
            current_basic[key] = value

    temps_list = []
    for row in soup.select(".city-forecast-tabs__row")[:7]:  # 取前7天的数据
        date = row.select_one(".date-bg .date").get_text(strip=True)
        temps = [span.get_text(strip=True) for span in row.select(".tmp-cont .temp")]
        high_temp, low_temp = (temps[0], temps[-1]) if len(temps) >= 2 else (None, None)
        temps_list.append((date, high_temp, low_temp))

    return city_name, current_abstract, current_basic, temps_list


@register_function('get_weather', GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_weather(conn, location: str = None, lang: str = "zh_CN"):
    api_key = conn.config["plugins"]["get_weather"]["api_key"]
    default_location = conn.config["plugins"]["get_weather"]["default_location"]
    location = location or conn.client_ip_info.get("city") or default_location
    logger.bind(tag=TAG).debug(f"获取天气: {location}")

    city_info = fetch_city_info(location, api_key)
    if not city_info:
        return ActionResponse(Action.REQLLM, f"未找到相关的城市: {location}，请确认地点是否正确", None)

    soup = fetch_weather_page(city_info['fxLink'])
    if not soup:
        return ActionResponse(Action.REQLLM, None, "请求失败")

    city_name, current_abstract, current_basic, temps_list = parse_weather_info(soup)
    weather_report = f"根据下列数据，用{lang}回应用户的查询天气请求：\n{city_name}未来7天天气:\n"
    for i, (date, high, low) in enumerate(temps_list):
        if high and low:
            weather_report += f"{date}: {low}到{high}\n"
    weather_report += (
        f"当前天气: {current_abstract}\n"
        f"当前天气参数: {current_basic}\n"
        f"(确保只报告指定单日的气温范围，除非用户明确要求想要了解多日天气，如果未指定，默认报告今天的温度范围。"
        "参数为0的值不需要报告给用户，每次都报告体感温度，根据语境选择合适的参数内容告知用户，并对参数给出相应评价)"
    )

    return ActionResponse(Action.REQLLM, weather_report, None)
