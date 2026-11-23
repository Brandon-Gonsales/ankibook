import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.limits import (
    BULK_CARDS_MAX,
    CARD_TEXT_MAX,
    EXAMPLE_MAX,
    READING_MAX,
    reject_explicit_nulls,
)


class AnkiCardBase(BaseModel):
    """Fields shared by flashcard create and read payloads."""

    base_text: str = Field(min_length=1, max_length=CARD_TEXT_MAX)
    target_1: str = Field(min_length=1, max_length=CARD_TEXT_MAX)
    target_2: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    target_3: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    reading: Optional[str] = Field(default=None, min_length=1, max_length=READING_MAX)
    example_base: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_1: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_2: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_3: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_translation_order(self) -> "AnkiCardBase":
        if self.target_3 is not None and self.target_2 is None:
            raise ValueError("target_2 cannot be null if target_3 is specified")
        if self.example_target_3 is not None and self.example_target_2 is None:
            raise ValueError("example_target_2 cannot be null if example_target_3 is specified")
        return self


class AnkiCardCreate(AnkiCardBase):
    """Payload for creating a card inside the lesson from the route."""


class AnkiCardBulkCreate(BaseModel):
    """Payload for creating one or more cards atomically."""

    cards: list[AnkiCardCreate] = Field(min_length=1, max_length=BULK_CARDS_MAX)

    model_config = ConfigDict(extra="forbid")


class AnkiCardUpdate(BaseModel):
    """Partial payload for updating a flashcard."""

    base_text: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    target_1: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    target_2: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    target_3: Optional[str] = Field(default=None, min_length=1, max_length=CARD_TEXT_MAX)
    reading: Optional[str] = Field(default=None, min_length=1, max_length=READING_MAX)
    example_base: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_1: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_2: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)
    example_target_3: Optional[str] = Field(default=None, min_length=1, max_length=EXAMPLE_MAX)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_supplied_translation_order(self) -> "AnkiCardUpdate":
        reject_explicit_nulls(self, ("base_text", "target_1"))
        if (
            self.target_3 is not None
            and "target_2" in self.model_fields_set
            and self.target_2 is None
        ):
            raise ValueError("target_2 cannot be null if target_3 is specified")
        if (
            self.example_target_3 is not None
            and "example_target_2" in self.model_fields_set
            and self.example_target_2 is None
        ):
            raise ValueError("example_target_2 cannot be null if example_target_3 is specified")
        return self


class AnkiCardRead(AnkiCardBase):
    """Complete flashcard response."""

    id: uuid.UUID
    ankilection_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")

