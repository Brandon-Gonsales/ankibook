import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import CardState, ReviewRating, UserCardProgress
from app.services.srs import MIN_EASE, schedule_review


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("rating", "expected_state", "expected_days"),
    [
        (ReviewRating.AGAIN, CardState.LEARNING, 1 / 1440),
        (ReviewRating.HARD, CardState.LEARNING, 6 / 1440),
        (ReviewRating.GOOD, CardState.REVIEW, 1.0),
        (ReviewRating.EASY, CardState.REVIEW, 4.0),
    ],
)
def test_new_card_rating_transitions(
    rating: ReviewRating,
    expected_state: CardState,
    expected_days: float,
) -> None:
    result = schedule_review(None, rating, NOW)

    assert result.state is expected_state
    assert result.interval_days == pytest.approx(expected_days, abs=1e-6)
    assert result.due == NOW + timedelta(days=result.interval_days)
    assert result.reps == 1
    assert result.lapses == 0


def test_good_review_uses_current_ease_without_mutating_progress() -> None:
    progress = _progress(state=CardState.REVIEW, interval_days=10, ease=2.5, reps=3)

    result = schedule_review(progress, ReviewRating.GOOD, NOW)

    assert result.state is CardState.REVIEW
    assert result.interval_days == 25
    assert result.ease == 2.5
    assert result.reps == 4
    assert progress.interval_days == 10
    assert progress.reps == 3


def test_again_on_review_enters_relearning_and_counts_lapse() -> None:
    progress = _progress(
        state=CardState.REVIEW,
        interval_days=20,
        ease=1.35,
        reps=8,
        lapses=2,
    )

    result = schedule_review(progress, ReviewRating.AGAIN, NOW)

    assert result.state is CardState.RELEARNING
    assert result.ease == MIN_EASE
    assert result.lapses == 3
    assert result.reps == 9


def test_easy_review_increases_ease_and_interval() -> None:
    progress = _progress(state=CardState.REVIEW, interval_days=10, ease=2.5)

    result = schedule_review(progress, ReviewRating.EASY, NOW)

    assert result.interval_days == 32.5
    assert result.ease == 2.65


def test_relearning_good_returns_to_review() -> None:
    progress = _progress(state=CardState.RELEARNING, interval_days=10 / 1440)

    result = schedule_review(progress, ReviewRating.GOOD, NOW)

    assert result.state is CardState.REVIEW
    assert result.interval_days == 1


def test_scheduler_rejects_invalid_rating_and_naive_datetime() -> None:
    with pytest.raises(ValueError):
        schedule_review(None, 5, NOW)

    with pytest.raises(ValueError, match="timezone-aware"):
        schedule_review(None, ReviewRating.GOOD, NOW.replace(tzinfo=None))


def _progress(
    *,
    state: CardState,
    interval_days: float,
    ease: float = 2.5,
    reps: int = 0,
    lapses: int = 0,
) -> UserCardProgress:
    return UserCardProgress(
        user_id="firebase-user",
        ankicard_id=uuid.uuid4(),
        state=state.value,
        interval_days=interval_days,
        ease=ease,
        reps=reps,
        lapses=lapses,
    )
