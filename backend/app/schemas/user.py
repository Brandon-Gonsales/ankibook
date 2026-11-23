from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    """Public user representation."""

    id: str = Field(min_length=1, description="Firebase Authentication UID")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class UserStats(BaseModel):
    """Aggregated study and content statistics for a user."""

    user_id: str
    total_books: int = Field(default=0, ge=0)
    total_lections: int = Field(default=0, ge=0)
    total_cards: int = Field(default=0, ge=0)
    cards_due: int = Field(default=0, ge=0)
    total_reviews_logged: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True, extra="forbid")
