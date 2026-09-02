"""
Time Utility Module
Provides unified time retrieval functionality
"""

import cnlunar
from datetime import datetime



def get_current_time() -> str:
    """
    Get current time string (format: HH:MM)
    """
    return datetime.now().strftime("%H:%M")


def get_current_date() -> str:
    """
    Get today's date string (format: YYYY-MM-DD)
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_current_weekday() -> str:
    """
    Get today's weekday
    """
    now = datetime.now()
    return now.strftime("%A")


def get_current_lunar_date() -> str:
    """
    Get lunar date string
    """
    try:
        now = datetime.now()
        today_lunar = cnlunar.Lunar(now, godType="8char")
        return "%s Year %s%s" % (
            today_lunar.lunarYearCn,
            today_lunar.lunarMonthCn[:-1],
            today_lunar.lunarDayCn,
        )
    except Exception:
        return "Failed to get lunar date"


def get_current_time_info() -> tuple:
    """
    Get current time information
    Returns: (current time string, today date, today weekday, lunar date)
    """
    current_time = get_current_time()
    today_date = get_current_date()
    today_weekday = get_current_weekday()
    lunar_date = get_current_lunar_date()
    
    return current_time, today_date, today_weekday, lunar_date
