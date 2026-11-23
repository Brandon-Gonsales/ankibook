import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ankilection import Ankilection
    from app.models.review_log import ReviewLog
    from app.models.user_card_progress import UserCardProgress


class AnkiCard(SQLModel, table=True):
    """AnkiCard entity matching public.ankicards table."""

    __tablename__ = "ankicards"
    __table_args__ = (
        Index("ankicards_idx_ankicards_ankilection_id", "ankilection_id"),
        CheckConstraint(
            "target_2 IS NOT NULL OR target_3 IS NULL",
            name="chk_ankicards_target_order",
        ),
        CheckConstraint(
            "example_target_2 IS NOT NULL OR example_target_3 IS NULL",
            name="chk_ankicards_example_target_order",
        ),
        ForeignKeyConstraint(
            ["ankilection_id"],
            ["public.ankilections.id"],
            name="fk_ankicards_ankilection_id_ankilections_id",
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
    ankilection_id: uuid.UUID = Field(
        nullable=False,
    )
    base_text: str = Field(
        nullable=False,
    )
    target_1: str = Field(
        nullable=False,
    )
    target_2: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    target_3: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    reading: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    example_base: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    example_target_1: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    example_target_2: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    example_target_3: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    # Relationships
    ankilection: Optional["Ankilection"] = Relationship(
        back_populates="ankicards",
    )
    card_progress: List["UserCardProgress"] = Relationship(
        back_populates="ankicard",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    review_logs: List["ReviewLog"] = Relationship(
        back_populates="ankicard",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
