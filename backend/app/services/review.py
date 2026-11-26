import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.models.review_log import ReviewLog
from app.repositories.review import ReviewRepository
from app.schemas.review_log import (
    DueCardRead,
    ReviewLogCreate,
    ReviewLogRead,
    ReviewResult,
    StudySummaryRead,
)
from app.schemas.user_card_progress import UserCardProgressRead
from app.services.srs import schedule_review
from app.services.study_day import next_study_day_start, study_day_start

MAX_EXTRA_NEW = 100


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
        extra_new: int = 0,
    ) -> list[DueCardRead]:
        """Cards to study now.

        * One book or lesson: its due cards plus all its new cards.
        * General ("Repasar"): every due card plus new cards up to what is
          left of today's limit, raised by ``extra_new`` ("learn more").
        """
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not 0 <= extra_new <= MAX_EXTRA_NEW:
            raise ValueError(f"extra_new must be between 0 and {MAX_EXTRA_NEW}")
        due_at = due_at or datetime.now(timezone.utc)

        new_limit: int | None = None
        if book_id is None and lection_id is None:
            new_limit = await self._new_left_today(user_id, due_at) + extra_new

        return await self.repository.list_due_cards(
            user_id,
            due_at=due_at,
            limit=limit,
            book_id=book_id,
            lection_id=lection_id,
            new_limit=new_limit,
        )

    async def get_summary(
        self,
        user_id: str,
        *,
        now: datetime | None = None,
    ) -> StudySummaryRead:
        now = now or datetime.now(timezone.utc)
        day_start = study_day_start(now)
        tomorrow_start = next_study_day_start(now)
        # End of tomorrow's study day: everything due before it lands tomorrow
        # (or earlier, if it is left undone today).
        horizon = tomorrow_start + (tomorrow_start - day_start)

        counts = await self.repository.study_counts(user_id, now=now, horizon=horizon)
        started = await self.repository.count_new_started_since(user_id, day_start)
        reviews = await self.repository.count_reviews_since(user_id, day_start)

        limit = settings.SRS_NEW_CARDS_PER_DAY
        new_today = min(max(0, limit - started), counts.new_available)
        tomorrow_new = min(limit, max(0, counts.new_remaining - new_today))
        return StudySummaryRead(
            due_now=counts.due_now,
            new_today=new_today,
            new_limit=limit,
            new_started_today=started,
            new_remaining=counts.new_remaining,
            reviews_today=reviews,
            next_due=counts.next_due if counts.due_now == 0 else None,
            tomorrow=counts.due_before_horizon + tomorrow_new,
            books=counts.books,
        )

    async def bury(
        self,
        user_id: str,
        card_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> datetime:
        """Hide a card until tomorrow's study day without grading it.

        Interval, ease and history stay untouched; a never-seen card gets a
        "new" progress row so it comes back tomorrow still as a new card.
        """
        card = await self.repository.get_owned_card(user_id, card_id)
        if card is None:
            raise ReviewCardNotFoundError("card not found")
        until = next_study_day_start(now or datetime.now(timezone.utc))
        try:
            progress = await self.repository.get_or_create_progress_for_update(
                user_id,
                card_id,
            )
            progress.due = until
            await self.repository.flush()
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return until

    async def _new_left_today(self, user_id: str, now: datetime) -> int:
        started = await self.repository.count_new_started_since(
            user_id,
            study_day_start(now),
        )
        return max(0, settings.SRS_NEW_CARDS_PER_DAY - started)

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
