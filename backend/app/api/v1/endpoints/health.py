from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import check_database_connection

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    app: str
    version: str
    environment: str
    timestamp: datetime
    database: Dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Check the operational status of the API and its connection to PostgreSQL/Supabase.",
)
async def health_check() -> HealthResponse:
    """Return system and database health status."""
    db_status = await check_database_connection()

    overall_status = "healthy" if db_status.get("healthy") else "degraded"

    return HealthResponse(
        status=overall_status,
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
    )
