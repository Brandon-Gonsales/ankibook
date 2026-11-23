import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, text
from sqlmodel import Field, SQLModel


class UserBook(SQLModel, table=True):
    """A public book another user added to their study library.

    Books are readable by every authenticated user, but only the author can
    edit them. A user studies their own books plus the ones listed here.
    """

    __tablename__ = "user_books"
    __table_args__ = (
        Index("user_books_idx_user_books_ankibook_id", "ankibook_id"),
        ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_user_books_user_id_users_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["ankibook_id"],
            ["public.ankibooks.id"],
            name="fk_user_books_ankibook_id_ankibooks_id",
            ondelete="CASCADE",
        ),
        {"schema": "public"},
    )

    user_id: str = Field(primary_key=True, nullable=False)
    ankibook_id: uuid.UUID = Field(primary_key=True, nullable=False)
    added_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )
