import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKeyConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ankibook import Ankibook
    from app.models.ankicard import AnkiCard


class Ankilection(SQLModel, table=True):
    """Ankilection entity matching public.ankilections table."""

    __tablename__ = "ankilections"
    __table_args__ = (
        Index("ankilections_idx_ankilections_ankibook_id", "ankibook_id"),
        ForeignKeyConstraint(
            ["ankibook_id"],
            ["public.ankibooks.id"],
            name="fk_ankilections_ankibook_id_ankibooks_id",
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
    ankibook_id: uuid.UUID = Field(
        nullable=False,
    )
    name: str = Field(
        nullable=False,
    )
    position: int = Field(
        default=0,
        nullable=False,
    )

    # Relationships
    ankibook: Optional["Ankibook"] = Relationship(
        back_populates="ankilections",
    )
    ankicards: List["AnkiCard"] = Relationship(
        back_populates="ankilection",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
