import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.limits import DESCRIPTION_MAX, TITLE_MAX, reject_explicit_nulls


class AnkibookBase(BaseModel):
    """Fields shared by Ankibook create and read payloads."""

    title: str = Field(min_length=1, max_length=TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    target_lang: str = Field(min_length=2, max_length=10)
    base_lang: str = Field(default="es", min_length=2, max_length=10)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_different_languages(self) -> "AnkibookBase":
        if self.target_lang.casefold() == self.base_lang.casefold():
            raise ValueError("target_lang must be different from base_lang")
        return self


class AnkibookCreate(AnkibookBase):
    """Payload for creating a book; author_id comes from authentication."""


class AnkibookUpdate(BaseModel):
    """Partial payload for updating a book."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    target_lang: Optional[str] = Field(default=None, min_length=2, max_length=10)
    base_lang: Optional[str] = Field(default=None, min_length=2, max_length=10)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_supplied_languages(self) -> "AnkibookUpdate":
        reject_explicit_nulls(self, ("title", "target_lang", "base_lang"))
        if (
            self.target_lang is not None
            and self.base_lang is not None
            and self.target_lang.casefold() == self.base_lang.casefold()
        ):
            raise ValueError("target_lang must be different from base_lang")
        return self


class AnkibookRead(AnkibookBase):
    """Book response with aggregate child counts."""

    id: uuid.UUID
    author_id: str
    created_at: datetime
    lections_count: int = Field(default=0, ge=0)
    cards_count: int = Field(default=0, ge=0)
    is_owner: bool = Field(default=False, description="The current user authored the book")
    is_added: bool = Field(default=False, description="The current user added it to their library")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class AnkibookDetail(AnkibookRead):
    """Book response including its ordered lessons."""

    ankilections: list["AnkilectionRead"] = Field(default_factory=list)


from app.schemas.ankilection import AnkilectionRead  # noqa: E402

AnkibookDetail.model_rebuild()
