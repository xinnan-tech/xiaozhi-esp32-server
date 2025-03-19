from datetime import datetime
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_time_function_desc = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前时间、日期、星期几",
        "parameters": {}
    }
}


@register_function('get_time', get_time_function_desc, ToolType.WAIT)
def get_time():
    """
    获取当前时间、日期、星期几
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    current_weekday = now.strftime("%A")
    response_text = f"当前日期: {current_date}，当前时间: {current_time}，星期: {current_weekday}"

    return ActionResponse(Action.REQLLM, response_text, None)