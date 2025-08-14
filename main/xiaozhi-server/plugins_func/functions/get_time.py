from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "Used for getting Indian calendar and Hindu almanac information for specific dates. "
            "Users can specify query content such as: Hindu calendar date, Vikram Samvat year, "
            "Hindu months, tithis, nakshatras, festivals, auspicious times (muhurat), etc. "
            "If no query content is specified, defaults to current Hindu calendar date and Vikram Samvat year. "
            "For basic queries like 'what's today's Hindu date', use context information directly instead of calling this tool."
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
    Used to get current Indian/Hindu calendar information including Vikram Samvat year,
    Hindu months, tithis, nakshatras, festivals, and auspicious times
    """
    from core.utils.cache.manager import cache_manager, CacheType

    # If date parameter is provided, use specified date; otherwise use current date
    import pytz

    if date:
        try:
            now = datetime.strptime(date, "%Y-%m-%d")
            # Convert to IST
            ist = pytz.timezone('Asia/Kolkata')
            now = ist.localize(now)
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                f"Date format error. Please use YYYY-MM-DD format, e.g., 2024-01-01",
                None,
            )
    else:
        # Use Indian Standard Time
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

    current_date = now.strftime("%Y-%m-%d")

    # If query is None, use default text
    if query is None:
        query = "default query for Hindu calendar date and Vikram Samvat year"

    # Try to get Indian calendar information from cache
    indian_cache_key = f"indian_calendar_info_{current_date}"
    cached_indian_info = cache_manager.get(CacheType.LUNAR, indian_cache_key)

    if cached_indian_info:
        return ActionResponse(Action.REQLLM, cached_indian_info, None)

    response_text = f"Please respond to the user's query based on the following information, providing details related to {query}:\n"

    # Indian Calendar Information
    try:
        # Basic Indian date formatting
        indian_months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Calculate approximate Vikram Samvat year (Gregorian + 57)
        vikram_year = now.year + 57

        # Hindu month names (approximate mapping)
        hindu_months = [
            "Paush", "Magh", "Falgun", "Chaitra", "Vaishakh", "Jyeshtha",
            "Ashadh", "Shravan", "Bhadrapada", "Ashwin", "Kartik", "Margashirsha"
        ]

        hindu_month = hindu_months[now.month - 1]

        response_text += (
            "Indian Calendar Information:\n"
            f"Gregorian Date: {now.strftime('%d %B %Y')}\n"
            f"Vikram Samvat Year: {vikram_year}\n"
            f"Hindu Month: {hindu_month}\n"
            f"Day of Week: {now.strftime('%A')}\n"
            f"Indian Standard Time: {now.strftime('%I:%M %p IST')}\n"
            "\nNote: For precise Hindu calendar calculations including tithis, nakshatras, and muhurat times, "
            "please consult a detailed panchang or install specialized Indian calendar libraries.\n"
            "\nCommon Indian Festivals and Observances:\n"
            "- Check local panchang for accurate festival dates\n"
            "- Amavasya (New Moon) and Purnima (Full Moon) dates\n"
            "- Ekadashi observances\n"
            "- Regional festivals and celebrations\n"
            "\n(This is a basic implementation. For detailed Hindu calendar features, "
            "specialized libraries like 'pyephem' with Indian calendar extensions would be needed)"
        )

    except Exception as e:
        response_text += f"Error calculating Indian calendar information: {str(e)}\n"
        response_text += f"Fallback: Current date is {now.strftime('%d %B %Y')} (IST)"

    # Cache Indian calendar information
    cache_manager.set(CacheType.LUNAR, indian_cache_key, response_text)

    return ActionResponse(Action.REQLLM, response_text, None)
