from enum import Enum, IntEnum


class CardState(str, Enum):
    """Possible learning states for a card progress."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class ReviewDirection(str, Enum):
    """Direction of flashcard review."""

    BASE_TO_TARGET = "base_to_target"
    TARGET_TO_BASE = "target_to_base"


class ReviewRating(IntEnum):
    """User feedback used by the spaced-repetition scheduler."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4
