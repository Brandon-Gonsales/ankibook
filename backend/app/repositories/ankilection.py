import uuid

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ankibook import Ankibook
from app.models.ankicard import AnkiCard
from app.models.ankilection import Ankilection
from app.schemas.ankilection import (
    AnkilectionCreate,
    AnkilectionDetail,
    AnkilectionRead,
    AnkilectionUpdate,
)


class AnkilectionRepository:
    """CRUD and joined read queries for lessons (public reads, author-only writes)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: str,
        book_id: uuid.UUID,
        data: AnkilectionCreate,
    ) -> Ankilection | None:
        if not await self._owns_book(user_id, book_id):
            return None
        lection = Ankilection(ankibook_id=book_id, **data.model_dump())
        self.session.add(lection)
        await self.session.flush()
        return lection

    async def get_owned(
        self,
        user_id: str,
        lection_id: uuid.UUID,
    ) -> Ankilection | None:
        statement = (
            select(Ankilection)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .where(
                Ankilection.id == lection_id,
                Ankibook.author_id == user_id,
            )
        )
        return (await self.session.exec(statement)).one_or_none()

    async def list_for_book(
        self,
        user_id: str,
        book_id: uuid.UUID,
    ) -> list[AnkilectionRead]:
        """Lessons of any book: books are public to read."""
        statement = (
            select(
                Ankilection,
                func.count(AnkiCard.id).label("cards_count"),
            )
            .outerjoin(AnkiCard, AnkiCard.ankilection_id == Ankilection.id)
            .where(Ankilection.ankibook_id == book_id)
            .group_by(Ankilection.id)
            .order_by(Ankilection.position, Ankilection.id)
        )
        rows = (await self.session.exec(statement)).all()
        return [
            AnkilectionRead.model_validate(
                {**lection.model_dump(), "cards_count": cards_count}
            )
            for lection, cards_count in rows
        ]

    async def get_detail(
        self,
        user_id: str,
        lection_id: uuid.UUID,
    ) -> AnkilectionDetail | None:
        lection = await self.session.get(Ankilection, lection_id)
        if lection is None:
            return None

        from app.repositories.ankicard import AnkiCardRepository

        cards = await AnkiCardRepository(self.session).list_for_lection(
            user_id,
            lection_id,
        )
        return AnkilectionDetail.model_validate(
            {
                **lection.model_dump(),
                "cards_count": len(cards),
                "ankicards": cards,
            }
        )

    async def update(
        self,
        lection: Ankilection,
        data: AnkilectionUpdate,
    ) -> Ankilection:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(lection, field, value)
        self.session.add(lection)
        await self.session.flush()
        return lection

    async def delete(self, lection: Ankilection) -> None:
        await self.session.delete(lection)
        await self.session.flush()

    async def _owns_book(self, user_id: str, book_id: uuid.UUID) -> bool:
        statement = select(Ankibook.id).where(
            Ankibook.id == book_id,
            Ankibook.author_id == user_id,
        )
        return (await self.session.exec(statement)).first() is not None
