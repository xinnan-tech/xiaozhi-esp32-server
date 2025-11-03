"""
ORM Layer

Provides database models and data access for all entities.
Organized by business domain (agent, device, binding, etc.).
"""

from orm.base import (
    Base,
    get_db,
    init_database,
    close_database,
    get_session_maker,
)

from orm.agent import Agent, AgentRepository
from orm.device import Device, DeviceRepository
from orm.binding import DeviceAgentBinding, DeviceAgentBindingRepository

__all__ = [
    # Base infrastructure
    "Base",
    "get_db",
    "init_database",
    "close_database",
    "get_session_maker",
    
    # Agent domain
    "Agent",
    "AgentRepository",
    
    # Device domain
    "Device",
    "DeviceRepository",
    
    # Binding domain
    "DeviceAgentBinding",
    "DeviceAgentBindingRepository",
]
