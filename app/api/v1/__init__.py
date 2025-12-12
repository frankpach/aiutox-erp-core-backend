"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, automation, config, preferences, pubsub, reporting, users
from app.modules.products.api import router as products_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(pubsub.router, prefix="/pubsub", tags=["pubsub"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
api_router.include_router(reporting.router, prefix="/reporting", tags=["reporting"])

