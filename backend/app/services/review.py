import uuid
from datetime import datetime

from app.models.review_log import ReviewLog
from app.repositories.review import ReviewRepository
from app.schemas.review_log import (
    DueCardRead,
    ReviewLogCreate,
    ReviewLogRead,
    ReviewResult,
)
from app.schemas.user_card_progress import UserCardProgressRead
from app.services.srs import schedule_review


class ReviewCardNotFoundError(LookupError):
    """Raised when a card does not exist or does not belong to the user."""


class ReviewService:
    """Coordinate due-card reads and atomic review submissions."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    async def get_due_cards(
        self,
        user_id: str,
        *,
        due_at: datetime | None = None,
        limit: int = 20,
        book_id: uuid.UUID | None = None,
        lection_id: uuid.UUID | None = None,
    ) -> list[DueCardRead]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return await self.repository.list_due_cards(
            user_id,
            due_at=due_at,
            limit=limit,
            book_id=book_id,
            lection_id=lection_id,
        )

    async def submit_review(
        self,
        user_id: str,
        submission: ReviewLogCreate,
        *,
        reviewed_at: datetime | None = None,
    ) -> ReviewResult:
        card = await self.repository.get_owned_card(user_id, submission.ankicard_id)
        if card is None:
            raise ReviewCardNotFoundError("card not found")

        try:
            progress = await self.repository.get_or_create_progress_for_update(
                user_id,
                submission.ankicard_id,
            )
            update = schedule_review(progress, submission.rating, reviewed_at)

            progress.state = update.state.value
            progress.due = update.due
            progress.interval_days = update.interval_days
            progress.ease = update.ease
            progress.reps = update.reps
            progress.lapses = update.lapses
            progress.last_review = update.last_review

            review_log = ReviewLog(
                user_id=user_id,
                ankicard_id=submission.ankicard_id,
                direction=submission.direction.value,
                rating=int(submission.rating),
                reviewed_at=update.last_review,
            )
            self.repository.add_review_log(review_log)
            await self.repository.flush()
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise

        return ReviewResult(
            review_log=ReviewLogRead.model_validate(review_log),
            progress=UserCardProgressRead.model_validate(progress),
            next_due=progress.due,
            message="Review registered successfully",
        )
