import datetime
from typing import Dict, Tuple

# Global dictionary to store daily output word count for each device
_device_daily_output: Dict[Tuple[str, datetime.date], int] = {}

# Record the last check date
_last_check_date: datetime.date = None


def reset_device_output():
    """
    Reset daily output word count for all devices
    Call this function at 0:00 every day
    """
    _device_daily_output.clear()


def get_device_output(device_id: str) -> int:
    """
    Get device's output word count for today
    """
    current_date = datetime.datetime.now().date()
    return _device_daily_output.get((device_id, current_date), 0)


def add_device_output(device_id: str, char_count: int):
    """
    Add to device's output word count
    """
    current_date = datetime.datetime.now().date()
    global _last_check_date

    # If first call or date changed, clear counter
    if _last_check_date is None or _last_check_date != current_date:
        _device_daily_output.clear()
        _last_check_date = current_date

    current_count = _device_daily_output.get((device_id, current_date), 0)
    _device_daily_output[(device_id, current_date)
                         ] = current_count + char_count


def check_device_output_limit(device_id: str, max_output_size: int) -> bool:
    """
    Check if device exceeds output limit
    :return: True if exceeds limit, False if not
    """
    if not device_id:
        return False

    current_output = get_device_output(device_id)
    return current_output >= max_output_size
