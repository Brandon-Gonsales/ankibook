import uuid
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models import AnkiCard, ReviewRating, UserCardProgress
from app.repositories.review import StudyCounts
from app.schemas import ReviewLogCreate
from app.schemas.review_log import BookProgressRead
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


@pytest.fixture(autouse=True)
def study_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SRS_NEW_CARDS_PER_DAY", 20)
    monkeypatch.setattr(settings, "SRS_TIMEZONE", "America/La_Paz")
    monkeypatch.setattr(settings, "SRS_DAY_START_HOUR", 4)


@pytest.mark.asyncio
async def test_general_review_caps_new_cards_with_what_is_left_today() -> None:
    repository = FakeReviewRepository(uuid.uuid4(), started_today=12)
    service = ReviewService(repository)  # type: ignore[arg-type]

    await service.get_due_cards("firebase-user", limit=50, due_at=NOW)

    assert repository.due_kwargs["new_limit"] == 8
    # NOW is 08:00 in Santa Cruz: the study day began at 04:00 local (08:00 UTC)
    assert repository.started_since == datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_general_review_never_goes_negative_and_accepts_extra() -> None:
    repository = FakeReviewRepository(uuid.uuid4(), started_today=35)
    service = ReviewService(repository)  # type: ignore[arg-type]

    await service.get_due_cards("firebase-user", due_at=NOW)
    assert repository.due_kwargs["new_limit"] == 0

    await service.get_due_cards("firebase-user", due_at=NOW, extra_new=20)
    assert repository.due_kwargs["new_limit"] == 20


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["book_id", "lection_id"])
async def test_book_or_lesson_study_is_not_limited(scope: str) -> None:
    repository = FakeReviewRepository(uuid.uuid4(), started_today=500)
    service = ReviewService(repository)  # type: ignore[arg-type]

    await service.get_due_cards("firebase-user", due_at=NOW, **{scope: uuid.uuid4()})

    assert repository.due_kwargs["new_limit"] is None


@pytest.mark.asyncio
async def test_extra_new_is_bounded() -> None:
    service = ReviewService(FakeReviewRepository(uuid.uuid4()))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="extra_new"):
        await service.get_due_cards("firebase-user", extra_new=101)


@pytest.mark.asyncio
async def test_summary_combines_limit_progress_and_forecast() -> None:
    book_id = uuid.uuid4()
    next_due = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    counts = StudyCounts(
        due_now=0,
        due_before_horizon=30,
        next_due=next_due,
        new_available=500,
        new_remaining=600,
        books=[BookProgressRead(book_id=book_id, total=883, new=600, learning=40, learned=243)],
    )
    repository = FakeReviewRepository(
        uuid.uuid4(), started_today=5, counts=counts, reviews_today=70
    )
    service = ReviewService(repository)  # type: ignore[arg-type]

    summary = await service.get_summary("firebase-user", now=NOW)

    assert summary.new_today == 15
    assert summary.new_limit == 20
    assert summary.new_started_today == 5
    assert summary.new_remaining == 600
    assert summary.reviews_today == 70
    assert summary.due_now == 0
    assert summary.next_due == next_due
    assert summary.tomorrow == 30 + 20
    assert summary.books[0].learned == 243
    # Tomorrow's study day ends at 04:00 local two days ahead (08:00 UTC on the 21st)
    assert repository.horizon == datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_summary_new_today_limited_by_available_cards() -> None:
    counts = StudyCounts(due_now=4, new_available=3, new_remaining=3)
    repository = FakeReviewRepository(uuid.uuid4(), counts=counts)
    service = ReviewService(repository)  # type: ignore[arg-type]

    summary = await service.get_summary("firebase-user", now=NOW)

    assert summary.new_today == 3
    assert summary.tomorrow == 0
    assert summary.next_due is None


@pytest.mark.asyncio
async def test_bury_moves_card_to_tomorrow_without_grading() -> None:
    card_id = uuid.uuid4()
    repository = FakeReviewRepository(card_id)
    repository.progress.state = "review"
    repository.progress.interval_days = 6.25
    repository.progress.ease = 2.35
    repository.progress.reps = 4
    service = ReviewService(repository)  # type: ignore[arg-type]

    until = await service.bury("firebase-user", card_id, now=NOW)

    assert until == datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
    assert repository.progress.due == until
    assert repository.progress.state == "review"
    assert repository.progress.interval_days == 6.25
    assert repository.progress.ease == 2.35
    assert repository.progress.reps == 4
    assert repository.review_log is None
    assert repository.committed is True


@pytest.mark.asyncio
async def test_bury_hides_foreign_card() -> None:
    repository = FakeReviewRepository(uuid.uuid4(), owns_card=False)
    service = ReviewService(repository)  # type: ignore[arg-type]

    with pytest.raises(ReviewCardNotFoundError):
        await service.bury("firebase-user", uuid.uuid4(), now=NOW)

    assert repository.committed is False


class FakeReviewRepository:
    def __init__(
        self,
        card_id: uuid.UUID,
        *,
        owns_card: bool = True,
        fail_flush: bool = False,
        started_today: int = 0,
        reviews_today: int = 0,
        counts: StudyCounts | None = None,
    ) -> None:
        self.started_today = started_today
        self.reviews_today = reviews_today
        self.counts = counts or StudyCounts()
        self.due_kwargs: dict = {}
        self.started_since: datetime | None = None
        self.horizon: datetime | None = None
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
        self.due_kwargs = kwargs
        return []

    async def count_new_started_since(self, user_id: str, since: datetime) -> int:
        self.started_since = since
        return self.started_today

    async def count_reviews_since(self, user_id: str, since: datetime) -> int:
        return self.reviews_today

    async def study_counts(
        self, user_id: str, *, now: datetime, horizon: datetime
    ) -> StudyCounts:
        self.horizon = horizon
        return self.counts

    def add_review_log(self, review_log) -> None:
        self.review_log = review_log

    async def flush(self) -> None:
        if self.fail_flush:
            raise RuntimeError("flush failed")
        if self.review_log is not None:
            self.review_log.id = 1

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
