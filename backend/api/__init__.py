"""API endpoint routers"""

from fastapi import APIRouter

# Import all routers
from .settings import router as settings_router
from .cameras import router as cameras_router
from .faces import router as faces_router
from .history import router as history_router
from .stats import router as stats_router

# Export all routers
__all__ = [
    'settings_router',
    'cameras_router',
    'faces_router',
    'history_router',
    'stats_router'
]
