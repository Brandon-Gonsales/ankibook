import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    REAL,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import CardState

if TYPE_CHECKING:
    from app.models.ankicard import AnkiCard
    from app.models.user import User


class UserCardProgress(SQLModel, table=True):
    """UserCardProgress entity matching public.user_card_progress table."""

    __tablename__ = "user_card_progress"
    __table_args__ = (
        Index("user_card_progress_idx_user_card_progress_user_id_due", "user_id", "due"),
        UniqueConstraint(
            "user_id",
            "ankicard_id",
            name="uq_user_card_progress_user_id_ankicard_id",
        ),
        CheckConstraint(
            "state IN ('new', 'learning', 'review', 'relearning')",
            name="chk_user_card_progress_state",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_user_card_progress_user_id_users_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["ankicard_id"],
            ["public.ankicards.id"],
            name="fk_user_card_progress_ankicard_id_ankicards_id",
            ondelete="CASCADE",
        ),
        {"schema": "public"},
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_id: str = Field(
        nullable=False,
        index=True,
        description="Firebase Auth UID of the user",
    )
    ankicard_id: uuid.UUID = Field(
        nullable=False,
        index=True,
    )
    state: str = Field(
        default=CardState.NEW.value,
        nullable=False,
    )
    due: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )
    interval_days: float = Field(
        default=0.0,
        nullable=False,
        sa_type=REAL,
    )
    ease: float = Field(
        default=2.5,
        nullable=False,
        sa_type=REAL,
    )
    reps: int = Field(
        default=0,
        nullable=False,
    )
    lapses: int = Field(
        default=0,
        nullable=False,
    )
    last_review: Optional[datetime] = Field(
        default=None,
        nullable=True,
        sa_type=DateTime(timezone=True),
    )

    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="card_progress",
    )
    ankicard: Optional["AnkiCard"] = Relationship(
        back_populates="card_progress",
    )
