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
)

from orm.agent import Agent, AgentRepository

# Future imports:
# from orm.device import Device, DeviceRepository
# from orm.binding import Binding, BindingRepository

__all__ = [
    # Base infrastructure
    "Base",
    "get_db",
    "init_database",
    "close_database",
    
    # Agent domain
    "Agent",
    "AgentRepository",
    
    # Future domains
    # "Device",
    # "DeviceRepository",
    # "Binding",
    # "BindingRepository",
]

