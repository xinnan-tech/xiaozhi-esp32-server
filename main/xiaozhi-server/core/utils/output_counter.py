import datetime
from typing import Dict, Tuple

# Global dictionary to store daily output character count for each device
_device_daily_output: Dict[Tuple[str, datetime.date], int] = {}
# Record the date of the last check
_last_check_date: datetime.date = None


def reset_device_output():
    """
    Reset daily output character count for all devices
    Called at 00:00 every day
    """
    _device_daily_output.clear()


def get_device_output(device_id: str) -> int:
    """
    Get the output character count for the device today
    """
    current_date = datetime.datetime.now().date()
    return _device_daily_output.get((device_id, current_date), 0)


def add_device_output(device_id: str, char_count: int):
    """
    Increase the output character count for the device
    """
    current_date = datetime.datetime.now().date()
    global _last_check_date

    # Clear counter if it's the first call or the date has changed
    if _last_check_date is None or _last_check_date != current_date:
        _device_daily_output.clear()
        _last_check_date = current_date

    current_count = _device_daily_output.get((device_id, current_date), 0)
    _device_daily_output[(device_id, current_date)] = current_count + char_count


def check_device_output_limit(device_id: str, max_output_size: int) -> bool:
    """
    Check if the device has exceeded the output limit
    :return: True if exceeded, False otherwise
    """
    if not device_id:
        return False
    current_output = get_device_output(device_id)
    return current_output >= max_output_size
