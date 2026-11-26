import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.review import ReviewRepository
from app.schemas.review_log import (
    DueCardRead,
    ReviewLogCreate,
    ReviewResult,
    StudySummaryRead,
)
from app.services.review import MAX_EXTRA_NEW, ReviewCardNotFoundError, ReviewService


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
    extra_new: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_EXTRA_NEW,
            description="General review only: new cards allowed beyond today's limit",
        ),
    ] = 0,
) -> list[DueCardRead]:
    """Cards to study now.

    Without a scope: due cards plus new cards up to today's limit
    (``SRS_NEW_CARDS_PER_DAY``). With a book or lesson: due + all its new cards.
    """
    service = ReviewService(ReviewRepository(session))
    return await service.get_due_cards(
        current_user.id,
        limit=limit,
        book_id=book_id,
        lection_id=lection_id,
        extra_new=extra_new,
    )


@router.get("/summary", response_model=StudySummaryRead)
async def study_summary(
    current_user: CurrentUser,
    session: DBSession,
) -> StudySummaryRead:
    """What is left to study today, the forecast for tomorrow and per-book progress."""
    service = ReviewService(ReviewRepository(session))
    return await service.get_summary(current_user.id)


@router.post("/{card_id}/bury", status_code=status.HTTP_204_NO_CONTENT)
async def bury_card(
    card_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """Leave a card for tomorrow without grading it."""
    service = ReviewService(ReviewRepository(session))
    try:
        await service.bury(current_user.id, card_id)
    except ReviewCardNotFoundError as exc:
        raise HTTPException(status_code=404, detail="AnkiCard not found") from exc


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
