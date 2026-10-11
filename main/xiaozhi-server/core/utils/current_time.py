"""
Time utility module
Provides unified time retrieval functionality
"""

from datetime import datetime

WEEKDAY_MAP = {
    "Monday": "Monday",
    "Tuesday": "Tuesday", 
    "Wednesday": "Wednesday",
    "Thursday": "Thursday",
    "Friday": "Friday",
    "Saturday": "Saturday",
    "Sunday": "Sunday",
}


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
    return WEEKDAY_MAP[now.strftime("%A")]


def get_current_date_formatted() -> str:
    """
    Get current date in a more readable format
    """
    try:
        now = datetime.now()
        return now.strftime("%B %d, %Y")
    except Exception:
        return "Failed to get date"


def get_current_time_info() -> tuple:
    """
    Get current time information
    Returns: (current time string, today's date, today's weekday, formatted date)
    """
    current_time = get_current_time()
    today_date = get_current_date()
    today_weekday = get_current_weekday()
    formatted_date = get_current_date_formatted()
    
    return current_time, today_date, today_weekday, formatted_date
