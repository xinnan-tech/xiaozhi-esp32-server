import requests
from bs4 import BeautifulSoup
from plugins_func.register import register_function,ToolType, ActionResponse, Action


get_weather_function_desc = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取某个地点的天气，用户应先提供一个位置，比如用户说杭州天气，参数为：zhejiang/hangzhou，比如用户说北京天气怎么样，参数为：beijing/beijing。如果用户只问天气怎么样，参数是:guangdong/guangzhou",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市，zhejiang/hangzhou"
                }
            },
            "required": [
                "city"
            ]
        }
    }
}

@register_function('get_weather', get_weather_function_desc, ToolType.WAIT)
def get_weather(city: str):
    """
    "获取某个地点的天气，用户应先提供一个位置，\n比如用户说杭州天气，参数为：zhejiang/hangzhou，\n\n比如用户说北京天气怎么样，参数为：beijing/beijing",
    city : 城市，zhejiang/hangzhou
    """
    url = "https://tianqi.moji.com/weather/china/"+city
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
