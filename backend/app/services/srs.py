from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.enums import CardState, ReviewRating
from app.models.user_card_progress import UserCardProgress


MIN_EASE = 1.3
LEARNING_AGAIN_DAYS = 1 / (24 * 60)
LEARNING_HARD_DAYS = 6 / (24 * 60)
RELEARNING_AGAIN_DAYS = 10 / (24 * 60)
GOOD_GRADUATING_DAYS = 1.0
EASY_GRADUATING_DAYS = 4.0
HARD_INTERVAL_FACTOR = 1.2
EASY_INTERVAL_BONUS = 1.3


@dataclass(frozen=True, slots=True)
class SRSUpdate:
    """Complete progress values produced by one review."""

    state: CardState
    due: datetime
    interval_days: float
    ease: float
    reps: int
    lapses: int
    last_review: datetime


def schedule_review(
    progress: UserCardProgress | None,
    rating: ReviewRating | int,
    reviewed_at: datetime | None = None,
) -> SRSUpdate:
    """Calculate the next schedule without mutating or persisting progress.

    The algorithm uses short learning/relearning steps and an ease-based review
    interval. Persistence and transaction locking belong to the repository layer.
    """
    rating = ReviewRating(rating)
    reviewed_at = reviewed_at or datetime.now(timezone.utc)
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at must be timezone-aware")

    state = CardState(progress.state) if progress else CardState.NEW
    interval = progress.interval_days if progress else 0.0
    ease = progress.ease if progress else 2.5
    reps = progress.reps if progress else 0
    lapses = progress.lapses if progress else 0

    if state in (CardState.NEW, CardState.LEARNING):
        next_state, next_interval = _schedule_learning(rating)
    elif state is CardState.RELEARNING:
        next_state, next_interval = _schedule_relearning(rating)
    else:
        next_state, next_interval, ease, did_lapse = _schedule_review(
            rating=rating,
            interval=max(interval, GOOD_GRADUATING_DAYS),
            ease=ease,
        )
        if did_lapse:
            lapses += 1

    next_interval = round(next_interval, 6)
    return SRSUpdate(
        state=next_state,
        due=reviewed_at + timedelta(days=next_interval),
        interval_days=next_interval,
        ease=round(max(MIN_EASE, ease), 2),
        reps=reps + 1,
        lapses=lapses,
        last_review=reviewed_at,
    )


def _schedule_learning(rating: ReviewRating) -> tuple[CardState, float]:
    if rating is ReviewRating.AGAIN:
        return CardState.LEARNING, LEARNING_AGAIN_DAYS
    if rating is ReviewRating.HARD:
        return CardState.LEARNING, LEARNING_HARD_DAYS
    if rating is ReviewRating.GOOD:
        return CardState.REVIEW, GOOD_GRADUATING_DAYS
    return CardState.REVIEW, EASY_GRADUATING_DAYS


def _schedule_relearning(rating: ReviewRating) -> tuple[CardState, float]:
    if rating is ReviewRating.AGAIN:
        return CardState.RELEARNING, RELEARNING_AGAIN_DAYS
    if rating is ReviewRating.HARD:
        return CardState.RELEARNING, 0.5
    if rating is ReviewRating.GOOD:
        return CardState.REVIEW, GOOD_GRADUATING_DAYS
    return CardState.REVIEW, 2.0


def _schedule_review(
    rating: ReviewRating,
    interval: float,
    ease: float,
) -> tuple[CardState, float, float, bool]:
    if rating is ReviewRating.AGAIN:
        return CardState.RELEARNING, RELEARNING_AGAIN_DAYS, ease - 0.2, True
    if rating is ReviewRating.HARD:
        return CardState.REVIEW, interval * HARD_INTERVAL_FACTOR, ease - 0.15, False
    if rating is ReviewRating.GOOD:
        return CardState.REVIEW, interval * ease, ease, False
    return CardState.REVIEW, interval * ease * EASY_INTERVAL_BONUS, ease + 0.15, False
