from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_time_function_desc = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前日期、时间和农历、黄历等信息",
        'parameters': {'type': 'object', 'properties': {}, 'required': []}
    }
}


@register_function('get_time', get_time_function_desc, ToolType.WAIT)
def get_time():
    """
    获取当前日期、时间和农历、黄历等信息
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    current_weekday = now.strftime("%A")
    response_text = f"根据以下信息，回应用户的时间查询请求，默认仅回应公历信息；如果用户询问阴历或农历日期，则回应农历日期；如果用户要求提供更多信息，则回应黄历信息\n"

    lunar = cnlunar.Lunar(now, godType='8char')
    response_text += (
        f"当前日期: {current_date}，当前时间: {current_time}，星期: {current_weekday}\n"
        "农历信息：\n"
        "%s年%s%s\n" % (lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn) +
        "干支: %s年 %s月 %s日\n" % (lunar.year8Char, lunar.month8Char, lunar.day8Char) +
        "生肖: 属%s\n" % (lunar.chineseYearZodiac) +
        "八字: %s\n" % (' '.join([lunar.year8Char, lunar.month8Char, lunar.day8Char, lunar.twohour8Char])) +
        "今日节日: %s\n" % (",".join(filter(None, (lunar.get_legalHolidays(), lunar.get_otherHolidays(), lunar.get_otherLunarHolidays())))) +
        "今日节气: %s\n" % (lunar.todaySolarTerms) +
        "下一节气: %s %s年%s月%s日\n" % (lunar.nextSolarTerm, lunar.nextSolarTermYear, lunar.nextSolarTermDate[0], lunar.nextSolarTermDate[1]) +
        "今年节气表: %s\n" % (', '.join([f"{term}({date[0]}月{date[1]}日)" for term, date in lunar.thisYearSolarTermsDic.items()])) +
        "生肖冲煞: %s\n" % (lunar.chineseZodiacClash) +
        "星座: %s\n" % (lunar.starZodiac) +
        "纳音: %s\n" % lunar.get_nayin() +
        "彭祖百忌: %s\n" % (lunar.get_pengTaboo(delimit=", ")) +
        "值日: %s执位\n" % lunar.get_today12DayOfficer()[0] +
        "值神: %s(%s)\n" % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2]) +
        "廿八宿: %s\n" % lunar.get_the28Stars() +
        "吉神方位: %s\n" % ' '.join(lunar.get_luckyGodsDirection()) +
        "今日胎神: %s\n" % lunar.get_fetalGod() +
        "宜: %s\n" % '、'.join(lunar.goodThing[:10]) +
        "忌: %s\n" % '、'.join(lunar.badThing[:10])
    )

    return ActionResponse(Action.REQLLM, response_text, None)