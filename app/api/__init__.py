"""API routers for CrawlDoctor."""

from app.api.tracking import router as tracking_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router

__all__ = [
    "tracking_router",
    "analytics_router",
    "auth_router", 
    "admin_router"
]
