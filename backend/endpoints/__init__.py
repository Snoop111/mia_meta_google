"""
Modular endpoint structure for MIA Marketing Intelligence Agent

Separated from the monolithic simple_adk_server.py for better maintainability
and to prevent file corruption during edits.
"""

from .auth_endpoints_simple import router as auth_router
from .meta_auth_endpoints import router as meta_auth_router
from .chat_endpoint import router as chat_router
from .creative_endpoint import router as creative_router
from .growth_endpoint import router as growth_router
from .optimize_endpoint import router as optimize_router
from .protect_endpoint import router as protect_router
from .static_endpoints import router as static_router

__all__ = [
    "auth_router",
    "meta_auth_router",
    "chat_router",
    "creative_router",
    "growth_router",
    "optimize_router",
    "protect_router",
    "static_router"
]