import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewDirection, ReviewRating
from app.schemas.ankicard import AnkiCardRead
from app.schemas.user_card_progress import UserCardProgressRead


class ReviewLogCreate(BaseModel):
    """Payload for grading a card; user_id comes from authentication."""

    ankicard_id: uuid.UUID
    direction: ReviewDirection = ReviewDirection.BASE_TO_TARGET
    rating: ReviewRating = Field(
        description="1=Again, 2=Hard, 3=Good, 4=Easy",
    )

    model_config = ConfigDict(extra="forbid")


class ReviewLogRead(ReviewLogCreate):
    """Persisted review log response."""

    id: int
    user_id: str
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ReviewResult(BaseModel):
    """Updated state returned after a successful review."""

    review_log: ReviewLogRead
    progress: UserCardProgressRead
    next_due: datetime
    message: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class DueCardRead(BaseModel):
    """Due card plus the context needed by the study screen."""

    card: AnkiCardRead
    progress: UserCardProgressRead | None = None
    lection_id: uuid.UUID
    lection_name: str
    book_id: uuid.UUID
    book_title: str
    target_lang: str = Field(description="Language being learned, for pronunciation")

    model_config = ConfigDict(extra="forbid")



class BookProgressRead(BaseModel):
    """How far the user is in one book they study."""

    book_id: uuid.UUID
    total: int = Field(ge=0)
    new: int = Field(ge=0, description="Never studied (or buried before their first review)")
    learning: int = Field(ge=0, description="Learning or relearning")
    learned: int = Field(ge=0, description="Graduated to review")

    model_config = ConfigDict(extra="forbid")


class StudySummaryRead(BaseModel):
    """Everything the home screen needs to say what to study today."""

    due_now: int = Field(ge=0, description="Seen cards due right now")
    new_today: int = Field(ge=0, description="New cards 'Repasar' will still give today")
    new_limit: int = Field(ge=0, description="Daily new-card limit")
    new_started_today: int = Field(ge=0, description="Cards seen for the first time today")
    new_remaining: int = Field(ge=0, description="Never-studied cards across the user's books")
    reviews_today: int = Field(ge=0, description="Ratings given today")
    streak: int = Field(
        ge=0,
        description="Consecutive study days with at least one review, up to today "
        "(or yesterday, while today is still pending)",
    )
    next_due: datetime | None = Field(
        default=None,
        description="Next moment a seen card becomes due, if none is due now",
    )
    tomorrow: int = Field(ge=0, description="Estimated cards for tomorrow (reviews + new)")
    books: list[BookProgressRead] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# The review endpoint and persistence service share the same validated payload.
ReviewSubmission = ReviewLogCreate
