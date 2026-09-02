from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "Strictly for Traditional Chinese Lunar Calendar, Almanac, and '24 Solar Terms' specific queries."
            "Use ONLY when user asks for Lunar date, Auspicious days, Zodiac, or specific traditional Solar terms."
            "DO NOT use for general questions about the Sun, Solar system, or astronomy (e.g. 'distance to sun')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to query, format YYYY-MM-DD. If not provided, use current date",
                },
                "query": {
                    "type": "string",
                    "description": "Content to query, e.g. lunar date, stems/branches, festivals, solar terms, zodiac, constellation, Bazi, taboos etc",
                },
            },
            "required": [],
        },
    },
}


@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(date=None, query=None):
    """
    Used to get current Lunar/Almanac info, and stems/branches, solar terms, zodiac, constellation, Bazi, taboos etc
    """
    from core.utils.cache.manager import cache_manager, CacheType

    # If date param provided, use it; else use current date
    if date:
        try:
            now = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                f"Date format error, please use YYYY-MM-DD, e.g.: 2024-01-01",
                None,
            )
    else:
        now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")

    # If query is None, use default text
    if query is None:
        query = "Default query stem-branch year and lunar date"

    # Try to get lunar info from cache
    lunar_cache_key = f"lunar_info_{current_date}"
    cached_lunar_info = cache_manager.get(CacheType.LUNAR, lunar_cache_key)
    if cached_lunar_info:
        return ActionResponse(Action.REQLLM, cached_lunar_info, None)

    response_text = f"Respond to user query based on following info, and provide info related to {query}:\n"

    lunar = cnlunar.Lunar(now, godType="8char")
    response_text += (
        "Lunar Info:\n"
        "%s Year %s %s\n" % (lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn)
        + "Stems/Branches: Year %s Month %s Day %s\n" % (lunar.year8Char, lunar.month8Char, lunar.day8Char)
        + "Zodiac: %s\n" % (lunar.chineseYearZodiac)
        + "Bazi: %s\n"
        % (
            " ".join(
                [lunar.year8Char, lunar.month8Char, lunar.day8Char, lunar.twohour8Char]
            )
        )
        + "Today's Festivals: %s\n"
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
        + "Today's Solar Term: %s\n" % (lunar.todaySolarTerms)
        + "Next Solar Term: %s %s-%s-%s\n"
        % (
            lunar.nextSolarTerm,
            lunar.nextSolarTermYear,
            lunar.nextSolarTermDate[0],
            lunar.nextSolarTermDate[1],
        )
        + "This Year's Solar Terms: %s\n"
        % (
            ", ".join(
                [
                    f"{term}(Month {date[0]} Day {date[1]})"
                    for term, date in lunar.thisYearSolarTermsDic.items()
                ]
            )
        )
        + "Zodiac Clash: %s\n" % (lunar.chineseZodiacClash)
        + "Constellation: %s\n" % (lunar.starZodiac)
        + "Nayin: %s\n" % lunar.get_nayin()
        + "Peng Zu Taboos: %s\n" % (lunar.get_pengTaboo(delimit=", "))
        + "Duty Day: %s\n" % lunar.get_today12DayOfficer()[0]
        + "Duty God: %s(%s)\n"
        % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2])
        + "28 Mansions: %s\n" % lunar.get_the28Stars()
        + "Lucky God Direction: %s\n" % " ".join(lunar.get_luckyGodsDirection())
        + "Fetal God: %s\n" % lunar.get_fetalGod()
        + "Auspicious: %s\n" % "、".join(lunar.goodThing[:10])
        + "Inauspicious: %s\n" % "、".join(lunar.badThing[:10])
        + "(Default returns stem-branch year and lunar date; Auspicious/Inauspicious only returned if requested)"
    )

    # Cache lunar info
    cache_manager.set(CacheType.LUNAR, lunar_cache_key, response_text)

    return ActionResponse(Action.REQLLM, response_text, None)
