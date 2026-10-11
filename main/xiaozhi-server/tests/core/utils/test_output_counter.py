"""Tests for the per-device daily output character counter."""
import pytest

from core.utils import output_counter


@pytest.fixture(autouse=True)
def _reset_counter():
    """Each test starts with a clean counter."""
    output_counter.reset_device_output()
    yield
    output_counter.reset_device_output()


def test_get_device_output_returns_zero_when_never_added():
    assert output_counter.get_device_output("dev-1") == 0


def test_add_device_output_increments_count():
    output_counter.add_device_output("dev-1", 100)
    output_counter.add_device_output("dev-1", 50)
    assert output_counter.get_device_output("dev-1") == 150


def test_add_device_output_is_per_device():
    output_counter.add_device_output("dev-1", 100)
    output_counter.add_device_output("dev-2", 200)
    assert output_counter.get_device_output("dev-1") == 100
    assert output_counter.get_device_output("dev-2") == 200


def test_check_device_output_limit_returns_true_when_exceeded():
    output_counter.add_device_output("dev-1", 100)
    assert output_counter.check_device_output_limit("dev-1", 100) is True
    assert output_counter.check_device_output_limit("dev-1", 50) is True


def test_check_device_output_limit_returns_false_when_under():
    output_counter.add_device_output("dev-1", 50)
    assert output_counter.check_device_output_limit("dev-1", 100) is False


def test_check_device_output_limit_with_empty_device_id_returns_false():
    assert output_counter.check_device_output_limit("", 1) is False
    assert output_counter.check_device_output_limit(None, 1) is False


def test_reset_clears_all_counts():
    output_counter.add_device_output("dev-1", 100)
    output_counter.add_device_output("dev-2", 200)
    output_counter.reset_device_output()
    assert output_counter.get_device_output("dev-1") == 0
    assert output_counter.get_device_output("dev-2") == 0