from fastapi import APIRouter
from app.api.v1.endpoints import (
    ankibooks,
    ankicards,
    ankilections,
    auth,
    health,
    reviews,
)

api_router = APIRouter()

# Include health routes under /api/v1
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(ankibooks.router)
api_router.include_router(ankilections.router)
api_router.include_router(ankicards.router)
api_router.include_router(reviews.router)
