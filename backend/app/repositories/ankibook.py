import uuid

from sqlalchemy import and_, distinct, exists, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ankibook import Ankibook
from app.models.ankicard import AnkiCard
from app.models.ankilection import Ankilection
from app.models.user_book import UserBook
from app.schemas.ankibook import (
    AnkibookCreate,
    AnkibookDetail,
    AnkibookRead,
    AnkibookUpdate,
)


def added_by(user_id: str):
    """SQL condition: the current row's book is in the user's library."""
    return exists().where(
        and_(UserBook.ankibook_id == Ankibook.id, UserBook.user_id == user_id)
    )


def studied_by(user_id: str):
    """SQL condition: the user authored the book or added it to their library."""
    return or_(Ankibook.author_id == user_id, added_by(user_id))


class AnkibookRepository:
    """CRUD and joined read queries for books.

    Every book is public to read; writes go through ``get_owned`` so only the
    author can change them.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: str, data: AnkibookCreate) -> Ankibook:
        book = Ankibook(author_id=user_id, **data.model_dump())
        self.session.add(book)
        await self.session.flush()
        return book

    async def get_owned(
        self,
        user_id: str,
        book_id: uuid.UUID,
    ) -> Ankibook | None:
        statement = select(Ankibook).where(
            Ankibook.id == book_id,
            Ankibook.author_id == user_id,
        )
        return (await self.session.exec(statement)).one_or_none()

    async def exists(self, book_id: uuid.UUID) -> bool:
        statement = select(Ankibook.id).where(Ankibook.id == book_id)
        return (await self.session.exec(statement)).first() is not None

    async def list_for_user(self, user_id: str) -> list[AnkibookRead]:
        """Books the user studies: their own plus the ones they added."""
        statement = (
            self._summary_statement(user_id)
            .where(studied_by(user_id))
            .order_by(Ankibook.created_at.desc())
        )
        rows = (await self.session.exec(statement)).all()
        return [self._to_read(user_id, *row) for row in rows]

    async def list_public(self, user_id: str) -> list[AnkibookRead]:
        """Every book, newest first, flagged for the current user."""
        statement = self._summary_statement(user_id).order_by(Ankibook.created_at.desc())
        rows = (await self.session.exec(statement)).all()
        return [self._to_read(user_id, *row) for row in rows]

    async def get_read(
        self,
        user_id: str,
        book_id: uuid.UUID,
    ) -> AnkibookRead | None:
        statement = self._summary_statement(user_id).where(Ankibook.id == book_id)
        row = (await self.session.exec(statement)).one_or_none()
        return self._to_read(user_id, *row) if row else None

    async def get_detail(
        self,
        user_id: str,
        book_id: uuid.UUID,
    ) -> AnkibookDetail | None:
        book = await self.get_read(user_id, book_id)
        if book is None:
            return None

        # Local import avoids coupling the repository modules at import time.
        from app.repositories.ankilection import AnkilectionRepository

        lections = await AnkilectionRepository(self.session).list_for_book(
            user_id,
            book_id,
        )
        return AnkibookDetail(**book.model_dump(), ankilections=lections)

    async def add_to_library(self, user_id: str, book_id: uuid.UUID) -> None:
        statement = (
            insert(UserBook)
            .values(user_id=user_id, ankibook_id=book_id)
            .on_conflict_do_nothing(index_elements=["user_id", "ankibook_id"])
        )
        await self.session.exec(statement)

    async def remove_from_library(self, user_id: str, book_id: uuid.UUID) -> None:
        statement = delete(UserBook).where(
            UserBook.user_id == user_id,
            UserBook.ankibook_id == book_id,
        )
        await self.session.exec(statement)

    async def update(
        self,
        book: Ankibook,
        data: AnkibookUpdate,
    ) -> Ankibook:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(book, field, value)
        self.session.add(book)
        await self.session.flush()
        return book

    async def delete(self, book: Ankibook) -> None:
        await self.session.delete(book)
        await self.session.flush()

    @staticmethod
    def _summary_statement(user_id: str):
        return (
            select(
                Ankibook,
                func.count(distinct(Ankilection.id)).label("lections_count"),
                func.count(distinct(AnkiCard.id)).label("cards_count"),
                added_by(user_id).label("is_added"),
            )
            .outerjoin(Ankilection, Ankilection.ankibook_id == Ankibook.id)
            .outerjoin(AnkiCard, AnkiCard.ankilection_id == Ankilection.id)
            .group_by(Ankibook.id)
        )

    @staticmethod
    def _to_read(
        user_id: str,
        book: Ankibook,
        lections_count: int,
        cards_count: int,
        is_added: bool,
    ) -> AnkibookRead:
        return AnkibookRead.model_validate(
            {
                **book.model_dump(),
                "lections_count": lections_count,
                "cards_count": cards_count,
                "is_owner": book.author_id == user_id,
                "is_added": bool(is_added),
            }
        )
