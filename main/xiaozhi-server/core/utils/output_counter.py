import datetime
from typing import Dict, Tuple

# 全局字典，用于存储每个设备的每日输出字数
_device_daily_output: Dict[Tuple[str, datetime.date], int] = {}
# 记录最后一次检查的日期
_last_check_date: datetime.date = None


def reset_device_output():
    """
    重置所有设备的每日输出字数
    每天0点调用此函数
    """
    _device_daily_output.clear()


def get_device_output(device_id: str) -> int:
    """
    获取设备当日的输出字数
    """
    current_date = datetime.datetime.now().date()
    return _device_daily_output.get((device_id, current_date), 0)


def add_device_output(device_id: str, char_count: int):
    """
    增加设备的输出字数
    """
    current_date = datetime.datetime.now().date()
    global _last_check_date

    # 如果是第一次调用或者日期发生变化，清空计数器
    if _last_check_date is None or _last_check_date != current_date:
        _device_daily_output.clear()
        _last_check_date = current_date

    current_count = _device_daily_output.get((device_id, current_date), 0)
    _device_daily_output[(device_id, current_date)] = current_count + char_count


def check_device_output_limit(device_id: str, max_output_size: int) -> bool:
    """
    检查设备是否超过输出限制
    :return: True 如果超过限制，False 如果未超过
    """
    if not device_id:
        return False
    current_output = get_device_output(device_id)
    return current_output >= max_output_size
