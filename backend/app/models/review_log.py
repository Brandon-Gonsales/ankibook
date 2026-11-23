import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    text,
)
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ankicard import AnkiCard
    from app.models.user import User


class ReviewLog(SQLModel, table=True):
    """ReviewLog entity matching public.review_log table."""

    __tablename__ = "review_log"
    __table_args__ = (
        Index("review_log_idx_review_log_user_id_reviewed_at", "user_id", "reviewed_at"),
        CheckConstraint(
            "direction IN ('base_to_target', 'target_to_base')",
            name="chk_review_log_direction",
        ),
        CheckConstraint(
            "rating BETWEEN 1 AND 4",
            name="chk_review_log_rating",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_review_log_user_id_users_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["ankicard_id"],
            ["public.ankicards.id"],
            name="fk_review_log_ankicard_id_ankicards_id",
            ondelete="CASCADE",
        ),
        {"schema": "public"},
    )

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        sa_column_kwargs={"autoincrement": True},
    )
    user_id: str = Field(
        nullable=False,
        index=True,
        description="Firebase Auth UID of the reviewer",
    )
    ankicard_id: uuid.UUID = Field(
        nullable=False,
        index=True,
    )
    direction: str = Field(
        nullable=False,
    )
    rating: int = Field(
        nullable=False,
        sa_type=SmallInteger,
    )
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="review_logs",
    )
    ankicard: Optional["AnkiCard"] = Relationship(
        back_populates="review_logs",
    )
