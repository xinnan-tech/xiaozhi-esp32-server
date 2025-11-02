"""
Agent ORM Module

Exports Agent model and repository for convenient importing.
"""

from orm.agent.model import Agent
from orm.agent.repository import AgentRepository

__all__ = ["Agent", "AgentRepository"]

