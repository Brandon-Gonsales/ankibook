import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CardState


class UserCardProgressRead(BaseModel):
    """Card progress returned by review and due-card queries."""

    id: uuid.UUID
    user_id: str
    ankicard_id: uuid.UUID
    state: CardState
    due: datetime
    interval_days: float = Field(ge=0)
    ease: float = Field(gt=0)
    reps: int = Field(ge=0)
    lapses: int = Field(ge=0)
    last_review: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
