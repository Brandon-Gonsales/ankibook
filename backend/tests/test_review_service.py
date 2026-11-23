import uuid
from datetime import datetime, timezone

import pytest

from app.models import AnkiCard, ReviewRating, UserCardProgress
from app.schemas import ReviewLogCreate
from app.services.review import ReviewCardNotFoundError, ReviewService


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_submit_review_updates_progress_and_commits() -> None:
    card_id = uuid.uuid4()
    repository = FakeReviewRepository(card_id)
    service = ReviewService(repository)  # type: ignore[arg-type]
    submission = ReviewLogCreate(ankicard_id=card_id, rating=ReviewRating.GOOD)

    result = await service.submit_review(
        "firebase-user",
        submission,
        reviewed_at=NOW,
    )

    assert result.review_log.id == 1
    assert result.review_log.rating is ReviewRating.GOOD
    assert result.progress.state.value == "review"
    assert result.progress.interval_days == 1
    assert result.next_due == result.progress.due
    assert repository.committed is True
    assert repository.rolled_back is False


@pytest.mark.asyncio
async def test_submit_review_hides_foreign_or_missing_card() -> None:
    repository = FakeReviewRepository(uuid.uuid4(), owns_card=False)
    service = ReviewService(repository)  # type: ignore[arg-type]
    submission = ReviewLogCreate(
        ankicard_id=uuid.uuid4(),
        rating=ReviewRating.AGAIN,
    )

    with pytest.raises(ReviewCardNotFoundError):
        await service.submit_review("firebase-user", submission, reviewed_at=NOW)

    assert repository.committed is False


@pytest.mark.asyncio
async def test_submit_review_rolls_back_on_persistence_error() -> None:
    card_id = uuid.uuid4()
    repository = FakeReviewRepository(card_id, fail_flush=True)
    service = ReviewService(repository)  # type: ignore[arg-type]
    submission = ReviewLogCreate(ankicard_id=card_id, rating=ReviewRating.EASY)

    with pytest.raises(RuntimeError, match="flush failed"):
        await service.submit_review("firebase-user", submission, reviewed_at=NOW)

    assert repository.committed is False
    assert repository.rolled_back is True


@pytest.mark.asyncio
async def test_due_card_limit_is_bounded() -> None:
    repository = FakeReviewRepository(uuid.uuid4())
    service = ReviewService(repository)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 1 and 100"):
        await service.get_due_cards("firebase-user", limit=101)


class FakeReviewRepository:
    def __init__(
        self,
        card_id: uuid.UUID,
        *,
        owns_card: bool = True,
        fail_flush: bool = False,
    ) -> None:
        self.card = (
            AnkiCard(
                id=card_id,
                ankilection_id=uuid.uuid4(),
                base_text="hola",
                target_1="hello",
            )
            if owns_card
            else None
        )
        self.progress = UserCardProgress(
            user_id="firebase-user",
            ankicard_id=card_id,
        )
        self.review_log = None
        self.fail_flush = fail_flush
        self.committed = False
        self.rolled_back = False

    async def get_owned_card(self, user_id: str, card_id: uuid.UUID):
        return self.card

    async def get_or_create_progress_for_update(
        self,
        user_id: str,
        card_id: uuid.UUID,
    ) -> UserCardProgress:
        return self.progress

    async def list_due_cards(self, user_id: str, **kwargs):
        return []

    def add_review_log(self, review_log) -> None:
        self.review_log = review_log

    async def flush(self) -> None:
        if self.fail_flush:
            raise RuntimeError("flush failed")
        self.review_log.id = 1

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
