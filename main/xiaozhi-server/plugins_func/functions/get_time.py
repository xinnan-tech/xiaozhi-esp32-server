from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

# 添加星期映射字典
WEEKDAY_MAP = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}

get_time_function_desc = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取今天日期或者当前时间信息",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


@register_function("get_time", get_time_function_desc, ToolType.WAIT)
def get_time():
    """
    获取当前的日期时间信息
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    current_weekday = WEEKDAY_MAP[now.strftime("%A")]
    response_text = (
        f"当前日期: {current_date}，当前时间: {current_time}， {current_weekday}"
    )

    return ActionResponse(Action.REQLLM, response_text, None)


get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "用于获取今天的阴历/农历和黄历信息。"
            "用户可以指定查询内容，如：阴历日期、天干地支、节气、生肖、星座、八字、宜忌等。"
            "如果没有指定查询内容，则默认查询干支年和农历日期。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要查询的内容，例如阴历日期、天干地支、节日、节气、生肖、星座、八字、宜忌等",
                }
            },
            "required": [],
        },
    },
}


@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(query=None):
    """
    用于获取当前的阴历/农历，和天干地支、节气、生肖、星座、八字、宜忌等黄历信息
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    current_weekday = WEEKDAY_MAP[now.strftime("%A")]

    # 如果 query 为 None，则使用默认文本
    if query is None:
        query = "默认查询干支年和农历日期"
    response_text = f"根据以下信息回应用户的查询请求，并提供与{query}相关的信息：\n"

    lunar = cnlunar.Lunar(now, godType="8char")
    response_text += (
        f"当前公历日期: {current_date}，当前时间: {current_time}，{current_weekday}\n"
        "农历信息：\n"
        "%s年%s%s\n" % (lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn)
        + "干支: %s年 %s月 %s日\n" % (lunar.year8Char, lunar.month8Char, lunar.day8Char)
        + "生肖: 属%s\n" % (lunar.chineseYearZodiac)
        + "八字: %s\n"
        % (
            " ".join(
                [lunar.year8Char, lunar.month8Char, lunar.day8Char, lunar.twohour8Char]
            )
        )
        + "今日节日: %s\n"
        % (
            ",".join(
                filter(
                    None,
                    (
                        lunar.get_legalHolidays(),
                        lunar.get_otherHolidays(),
                        lunar.get_otherLunarHolidays(),
                    ),
                )
            )
        )
        + "今日节气: %s\n" % (lunar.todaySolarTerms)
        + "下一节气: %s %s年%s月%s日\n"
        % (
            lunar.nextSolarTerm,
            lunar.nextSolarTermYear,
            lunar.nextSolarTermDate[0],
            lunar.nextSolarTermDate[1],
        )
        + "今年节气表: %s\n"
        % (
            ", ".join(
                [
                    f"{term}({date[0]}月{date[1]}日)"
                    for term, date in lunar.thisYearSolarTermsDic.items()
                ]
            )
        )
        + "生肖冲煞: %s\n" % (lunar.chineseZodiacClash)
        + "星座: %s\n" % (lunar.starZodiac)
        + "纳音: %s\n" % lunar.get_nayin()
        + "彭祖百忌: %s\n" % (lunar.get_pengTaboo(delimit=", "))
        + "值日: %s执位\n" % lunar.get_today12DayOfficer()[0]
        + "值神: %s(%s)\n"
        % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2])
        + "廿八宿: %s\n" % lunar.get_the28Stars()
        + "吉神方位: %s\n" % " ".join(lunar.get_luckyGodsDirection())
        + "今日胎神: %s\n" % lunar.get_fetalGod()
        + "宜: %s\n" % "、".join(lunar.goodThing[:10])
        + "忌: %s\n" % "、".join(lunar.badThing[:10])
        + "(默认返回干支年和农历日期；仅在要求查询宜忌信息时才返回本日宜忌)"
    )

    return ActionResponse(Action.REQLLM, response_text, None)
