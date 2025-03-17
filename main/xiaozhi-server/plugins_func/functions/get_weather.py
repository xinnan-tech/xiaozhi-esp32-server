import requests
from bs4 import BeautifulSoup
from plugins_func.register import register_function, ToolType, ActionResponse, Action


def get_city_by_ip() -> str:
    try:
        response = requests.get('http://ip-api.com/json', timeout=5)
        if response.status_code != 200:
            raise ValueError(f"API error: {response.text}")
        data = response.json()
        if data['status'] != 'success':
            raise ValueError(f"API error: {data.get('message', 'Unknown error')}")
        city = data['city']
        province = data['regionName']
        return f"{province}/{city}"
    except Exception as e:
        print(f"[定位失败] 使用默认位置，错误: {str(e)}")
        return None

get_weather_function_desc = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取某个地点的天气，用户应先提供一个位置，比如用户说杭州天气，参数为：zhejiang/hangzhou，比如用户说北京天气怎么样，参数为：beijing/beijing。如果用户只问天气怎么样，则没有参数，系统会自动定位城市。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "可选，格式：省份拼音/城市拼音，如 beijing/beijing"
                }
            },
            "required": []
        }
    }
}


@register_function('get_weather', get_weather_function_desc, ToolType.WAIT)
def get_weather(city: str = None):
    """
    获取某个地点的天气，用户应先提供一个位置，
    比如用户说杭州天气，参数为：zhejiang/hangzhou，
    比如用户说北京天气怎么样，参数为：beijing/beijing
    city : 城市，zhejiang/hangzhou
    """
    if not city:
        city = get_city_by_ip()
        print(f"[天气查询] 自动定位城市: {city}")
    
    url = f"https://tianqi.moji.com/weather/china/{city}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code!=200:
        return ActionResponse(Action.REQLLM, None, "请求失败")
    soup = BeautifulSoup(response.text, "html.parser")
    weather = soup.find('meta', attrs={'name':'description'})["content"]
    weather = weather.replace("墨迹天气", "")
    return ActionResponse(Action.REQLLM, weather, None)
