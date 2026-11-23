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

    model_config = ConfigDict(extra="forbid")



# The review endpoint and persistence service share the same validated payload.
ReviewSubmission = ReviewLogCreate
