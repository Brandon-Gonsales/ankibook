import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.limits import POSITION_MAX, TITLE_MAX, reject_explicit_nulls


class AnkilectionBase(BaseModel):
    """Fields shared by lesson create and read payloads."""

    name: str = Field(min_length=1, max_length=TITLE_MAX)
    position: int = Field(default=0, ge=0, le=POSITION_MAX)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnkilectionCreate(AnkilectionBase):
    """Payload for creating a lesson inside the book from the route."""


class AnkilectionUpdate(BaseModel):
    """Partial payload for updating or reordering a lesson."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX)
    position: Optional[int] = Field(default=None, ge=0, le=POSITION_MAX)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_no_nulls(self) -> "AnkilectionUpdate":
        reject_explicit_nulls(self, ("name", "position"))
        return self


class AnkilectionRead(AnkilectionBase):
    """Lesson response with its card count."""

    id: uuid.UUID
    ankibook_id: uuid.UUID
    cards_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class AnkilectionDetail(AnkilectionRead):
    """Lesson response including all its flashcards."""

    ankicards: list["AnkiCardRead"] = Field(default_factory=list)


from app.schemas.ankicard import AnkiCardRead  # noqa: E402

AnkilectionDetail.model_rebuild()
