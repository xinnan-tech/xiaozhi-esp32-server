"""Tests for core/utils/current_time.py.

Uses freezegun to control `datetime.now()` so the tests don't flake
around midnight, and to verify the weekday/date formatting logic.
"""
from datetime import datetime

import pytest
from freezegun import freeze_time

from core.utils import current_time


@freeze_time("2026-09-02 10:30:00")
def test_get_current_time_format_is_hh_mm():
    assert current_time.get_current_time() == "10:30"


@freeze_time("2026-09-02 23:59:59")
def test_get_current_time_at_late_hour():
    assert current_time.get_current_time() == "23:59"


@freeze_time("2026-09-02 10:30:00")
def test_get_current_date_format_is_iso():
    assert current_time.get_current_date() == "2026-09-02"


@freeze_time("2026-09-02 10:30:00")  # 2026-09-02 is a Wednesday
def test_get_current_weekday_returns_english_label():
    assert current_time.get_current_weekday() == "Wednesday"


def test_weekday_map_has_all_seven_days():
    assert set(current_time.WEEKDAY_MAP.keys()) == {
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    }
    # Western builds map each weekday to its English name.
    assert all(k == v for k, v in current_time.WEEKDAY_MAP.items())


@freeze_time("2026-09-02 10:30:00")
def test_get_current_time_info_returns_four_tuple():
    info = current_time.get_current_time_info()
    assert isinstance(info, tuple)
    assert len(info) == 4
    time_str, date_str, weekday, formatted_date = info
    assert time_str == "10:30"
    assert date_str == "2026-09-02"
    assert weekday == "Wednesday"
    assert formatted_date == "September 02, 2026"
