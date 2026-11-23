import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ankilection import Ankilection
    from app.models.user import User


class Ankibook(SQLModel, table=True):
    """Ankibook entity matching public.ankibooks table."""

    __tablename__ = "ankibooks"
    __table_args__ = (
        CheckConstraint("target_lang <> base_lang", name="chk_ankibooks_target_lang_ne_base_lang"),
        ForeignKeyConstraint(
            ["author_id"],
            ["public.users.id"],
            name="fk_ankibooks_author_id_users_id",
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
    author_id: str = Field(
        nullable=False,
        index=True,
        description="Firebase Auth UID of the author",
    )
    title: str = Field(
        nullable=False,
    )
    description: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    target_lang: str = Field(
        nullable=False,
    )
    base_lang: str = Field(
        default="es",
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    # Relationships
    author: Optional["User"] = Relationship(
        back_populates="ankibooks",
    )
    ankilections: List["Ankilection"] = Relationship(
        back_populates="ankibook",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True, "order_by": "Ankilection.position"},
    )
