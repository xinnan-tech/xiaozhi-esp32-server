"""
API Routers

FastAPI route handlers for all API endpoints.
"""

from router.agent import router as agent_router
from router.device import router as device_router
from router.binding import router as binding_router

__all__ = [
    "agent_router",
    "device_router",
    "binding_router",
]
