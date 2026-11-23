import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ankibook import Ankibook
from app.models.ankicard import AnkiCard
from app.models.ankilection import Ankilection
from app.schemas.ankicard import AnkiCardCreate, AnkiCardRead, AnkiCardUpdate


class AnkiCardRepository:
    """CRUD for flashcards (public reads, author-only writes)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: str,
        lection_id: uuid.UUID,
        data: AnkiCardCreate,
    ) -> AnkiCard | None:
        if not await self._owns_lection(user_id, lection_id):
            return None
        card = AnkiCard(ankilection_id=lection_id, **data.model_dump())
        self.session.add(card)
        await self.session.flush()
        return card

    async def create_bulk(
        self,
        user_id: str,
        lection_id: uuid.UUID,
        cards: list[AnkiCardCreate],
    ) -> list[AnkiCard] | None:
        if not await self._owns_lection(user_id, lection_id):
            return None
        models = [
            AnkiCard(ankilection_id=lection_id, **card.model_dump())
            for card in cards
        ]
        self.session.add_all(models)
        await self.session.flush()
        return models

    async def get_owned(
        self,
        user_id: str,
        card_id: uuid.UUID,
    ) -> AnkiCard | None:
        statement = (
            select(AnkiCard)
            .join(Ankilection, AnkiCard.ankilection_id == Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .where(AnkiCard.id == card_id, Ankibook.author_id == user_id)
        )
        return (await self.session.exec(statement)).one_or_none()

    async def get_visible(self, card_id: uuid.UUID) -> AnkiCard | None:
        """Any card by id: books are public to read."""
        return await self.session.get(AnkiCard, card_id)

    async def list_for_lection(
        self,
        user_id: str,
        lection_id: uuid.UUID,
    ) -> list[AnkiCardRead]:
        """Cards of any lesson: books are public to read."""
        statement = (
            select(AnkiCard)
            .where(AnkiCard.ankilection_id == lection_id)
            .order_by(AnkiCard.created_at, AnkiCard.id)
        )
        cards = (await self.session.exec(statement)).all()
        return [AnkiCardRead.model_validate(card) for card in cards]

    async def update(self, card: AnkiCard, data: AnkiCardUpdate) -> AnkiCard:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(card, field, value)
        self.session.add(card)
        await self.session.flush()
        return card

    async def delete(self, card: AnkiCard) -> None:
        await self.session.delete(card)
        await self.session.flush()

    async def _owns_lection(self, user_id: str, lection_id: uuid.UUID) -> bool:
        statement = (
            select(Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .where(
                Ankilection.id == lection_id,
                Ankibook.author_id == user_id,
            )
        )
        return (await self.session.exec(statement)).first() is not None
