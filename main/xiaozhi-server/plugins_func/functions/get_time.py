from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "Used for getting lunar calendar and Chinese almanac information for specific dates. "
            "Users can specify query content such as: lunar date, heavenly stems and earthly branches, "
            "solar terms, zodiac signs, constellations, eight characters, auspicious/inauspicious activities, etc. "
            "If no query content is specified, defaults to heavenly stems/earthly branches year and lunar date. "
            "For basic queries like 'what's today's lunar date', use context information directly instead of calling this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to query in YYYY-MM-DD format, e.g., 2024-01-01. If not provided, uses current date",
                },
                "query": {
                    "type": "string",
                    "description": "Content to query, e.g., lunar date, heavenly stems and earthly branches, festivals, solar terms, zodiac, constellation, eight characters, auspicious/inauspicious activities, etc.",
                },
            },
            "required": [],
        },
    },
}


@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(date=None, query=None):
    """
    Used to get current lunar calendar information including heavenly stems and earthly branches,
    solar terms, zodiac signs, constellations, eight characters, and auspicious/inauspicious activities
    """
    from core.utils.cache.manager import cache_manager, CacheType

    # If date parameter is provided, use specified date; otherwise use current date
    if date:
        try:
            now = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                f"Date format error. Please use YYYY-MM-DD format, e.g., 2024-01-01",
                None,
            )
    else:
        now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")

    # If query is None, use default text
    if query is None:
        query = "default query for heavenly stems/earthly branches year and lunar date"

    # Try to get lunar information from cache
    lunar_cache_key = f"lunar_info_{current_date}"
    cached_lunar_info = cache_manager.get(CacheType.LUNAR, lunar_cache_key)

    if cached_lunar_info:
        return ActionResponse(Action.REQLLM, cached_lunar_info, None)

    response_text = f"Please respond to the user's query based on the following information, providing details related to {query}:\n"

    lunar = cnlunar.Lunar(now, godType="8char")

    response_text += (
        "Lunar Calendar Information:\n"
        "%s Year %s %s\n" % (
            lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn)
        + "Heavenly Stems & Earthly Branches: %s Year %s Month %s Day\n" % (
            lunar.year8Char, lunar.month8Char, lunar.day8Char)
        + "Chinese Zodiac: %s\n" % (lunar.chineseYearZodiac)
        + "Eight Characters (Ba Zi): %s\n"
        % (
            " ".join(
                [lunar.year8Char, lunar.month8Char,
                    lunar.day8Char, lunar.twohour8Char]
            )
        )
        + "Today's Festivals: %s\n"
        % (
            ",".join(
                filter(
                    None,
                    [
                        lunar.get_legalHolidays(),
                        lunar.get_otherHolidays(),
                        lunar.get_otherLunarHolidays(),
                    ],
                )
            )
        )
        + "Today's Solar Term: %s\n" % (
            lunar.todaySolarTerms if lunar.todaySolarTerms else "None")
        + "Next Solar Term: %s %s Year %s Month %s Day\n"
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
                    f"{term}({date[0]}/{date[1]})"
                    for term, date in lunar.thisYearSolarTermsDic.items()
                ]
            )
        )
        + "Zodiac Clash: %s\n" % (lunar.chineseZodiacClash)
        + "Western Zodiac: %s\n" % (lunar.starZodiac)
        + "Nayin (Five Elements): %s\n" % lunar.get_nayin()
        + "Pengzu Taboos: %s\n" % (lunar.get_pengTaboo(delimit=", "))
        + "Day Officer: %s Position\n" % lunar.get_today12DayOfficer()[0]
        + "Duty God: %s (%s)\n"
        % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2])
        + "28 Lunar Mansions: %s\n" % lunar.get_the28Stars()
        + "Auspicious Directions: %s\n" % " ".join(lunar.get_luckyGodsDirection())
        + "Fetal God Position: %s\n" % lunar.get_fetalGod()
        + "Auspicious Activities: %s\n" % ", ".join(lunar.goodThing[:10])
        + "Inauspicious Activities: %s\n" % ", ".join(lunar.badThing[:10])
        + "(Default returns heavenly stems/earthly branches year and lunar date; detailed auspicious/inauspicious info only returned when specifically requested)"
    )

    # Cache lunar information
    cache_manager.set(CacheType.LUNAR, lunar_cache_key, response_text)

    return ActionResponse(Action.REQLLM, response_text, None)
