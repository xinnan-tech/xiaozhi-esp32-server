from fastapi import APIRouter
from api.v1 import user, templates, agents, voices, internal, files

api_router = APIRouter()

# User authentication routes
api_router.include_router(
    user.router,
    prefix="/user",
    tags=["Account","Authentication"]
)

# Template routes
api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Templates"]
)

# Agent routes
api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"]
)

# Voice routes
api_router.include_router(
    voices.router,
    prefix="/voices",
    tags=["Voices"]
)

# Internal routes (for xiaozhi-server)
api_router.include_router(
    internal.router,
    prefix="/internal",
    tags=["Internal"]
)

# File upload routes (for App only)
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["Files"]
)

