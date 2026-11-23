from typing import TYPE_CHECKING, List
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ankibook import Ankibook
    from app.models.review_log import ReviewLog
    from app.models.user_card_progress import UserCardProgress


class User(SQLModel, table=True):
    """User entity matching public.users table.
    
    Ultra-minimalist approach:
    Only stores the Firebase Authentication UID as the primary key.
    All user metadata (email, display name, password) resides solely in Firebase Auth.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: str = Field(
        primary_key=True,
        index=True,
        nullable=False,
        description="Firebase Auth UID as unique user identifier",
    )

    # Relationships
    ankibooks: List["Ankibook"] = Relationship(
        back_populates="author",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    card_progress: List["UserCardProgress"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    review_logs: List["ReviewLog"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
