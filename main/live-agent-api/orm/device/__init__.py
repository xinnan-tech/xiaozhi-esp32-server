"""
Device ORM Package

Exports Device model and repository.
"""

from .model import Device
from .repository import DeviceRepository

__all__ = ["Device", "DeviceRepository"]

