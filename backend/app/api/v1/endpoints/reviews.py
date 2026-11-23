import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.review import ReviewRepository
from app.schemas.review_log import DueCardRead, ReviewLogCreate, ReviewResult
from app.services.review import ReviewCardNotFoundError, ReviewService


router = APIRouter(prefix="/reviews", tags=["Reviews"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/due", response_model=list[DueCardRead])
async def list_due_cards(
    current_user: CurrentUser,
    session: DBSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    book_id: Annotated[
        uuid.UUID | None,
        Query(description="Study one book: its due cards plus its new cards"),
    ] = None,
    lection_id: Annotated[
        uuid.UUID | None,
        Query(description="Study one lesson: its due cards plus its new cards"),
    ] = None,
) -> list[DueCardRead]:
    """Cards to study now. Without a scope only due, already-seen cards are returned."""
    service = ReviewService(ReviewRepository(session))
    return await service.get_due_cards(
        current_user.id,
        limit=limit,
        book_id=book_id,
        lection_id=lection_id,
    )


@router.post("", response_model=ReviewResult, status_code=status.HTTP_201_CREATED)
async def submit_review(
    data: ReviewLogCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> ReviewResult:
    service = ReviewService(ReviewRepository(session))
    try:
        return await service.submit_review(current_user.id, data)
    except ReviewCardNotFoundError as exc:
        raise HTTPException(status_code=404, detail="AnkiCard not found") from exc
